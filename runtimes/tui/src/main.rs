use crossterm::{
    event::{self, Event, KeyCode, KeyEventKind, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    prelude::*,
    widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap},
};
use serde_json::{json, Value};
use std::{
    collections::VecDeque,
    env,
    io::{self, BufRead, BufReader, Write},
    os::fd::FromRawFd,
    os::unix::net::UnixStream,
    sync::mpsc,
    thread,
    time::{Duration, Instant},
};
const BG: Color = Color::Indexed(0);
const PANEL: Color = Color::Indexed(8);
const CORAL: Color = Color::Indexed(1);
const TEXT: Color = Color::Indexed(7);
const MUTED: Color = Color::Indexed(15);
const MINT: Color = Color::Indexed(2);
const CLAW: [&str; 9] = [
    "  ▄▄           ▄▄  ",
    " ████         ████ ",
    " ███▀  ▄▄▄▄▄  ▀███ ",
    "  ▀██▄██ ▀ ██▄██▀  ",
    "     ██ o o ██     ",
    "   ▄██ ▀▀▀▀▀ ██▄   ",
    "  ▀▀ ███████ ▀▀    ",
    "      █████        ",
    "     ▀▀   ▀▀       ",
];
fn palette(on: bool) -> io::Result<()> {
    let linux = env::var("TERM").unwrap_or_default() == "linux";
    let mut out = io::stdout();
    if on {
        for (i, color) in [
            "0c131d", "ff7063", "70dab8", "f1c982", "80a8e8", "bb9bf2", "8dd6e0", "e1e9f2",
            "14202f", "ffa194", "96e7cd", "f9dfab", "a5c2ef", "d6bdfb", "b6e8ee", "8ca1b4",
        ]
        .iter()
        .enumerate()
        {
            if linux {
                write!(out, "\x1b]P{i:x}{color}")?;
            } else {
                write!(out, "\x1b]4;{i};#{color}\x1b\\")?;
            }
        }
    } else if linux {
        write!(out, "\x1b]R")?;
    } else {
        write!(out, "\x1b]104\x1b\\")?;
    }
    out.flush()
}
fn clean(s: &str) -> String {
    s.chars()
        .filter(|c| !c.is_control() || *c == '\n' || *c == '\t')
        .collect()
}
fn send(s: &mut UnixStream, v: Value) -> io::Result<()> {
    writeln!(s, "{v}")
}
fn strval<'a>(v: &'a Value, key: &str) -> &'a str {
    v[key].as_str().unwrap_or("")
}
// Encode only the public verification address, never the device code or tokens.
fn login_qr(url: &str) -> Vec<Line<'static>> {
    if url != "https://auth.openai.com/codex/device" {
        return Vec::new();
    }
    let Ok(code) = qrcode::QrCode::new(url.as_bytes()) else {
        return Vec::new();
    };
    let width = code.width();
    let side = width + 8; // Four light modules on every side form the quiet zone.
    let dark = |x: usize, y: usize| {
        x >= 4
            && y >= 4
            && x < width + 4
            && y < width + 4
            && code[(x - 4, y - 4)] == qrcode::Color::Dark
    };
    (0..side)
        .step_by(2)
        .map(|y| {
            let row: String = (0..side)
                .map(|x| match (dark(x, y), dark(x, y + 1)) {
                    (true, true) => '█',
                    (true, false) => '▀',
                    (false, true) => '▄',
                    (false, false) => ' ',
                })
                .collect();
            Line::styled(row, Style::default().fg(BG).bg(TEXT))
        })
        .collect()
}

fn device_lines(screen: &Value, width: u16, height: u16) -> Vec<Line<'static>> {
    let url = strval(screen, "url");
    let mut lines = vec![Line::styled(clean(url), Style::default().fg(MINT))];
    let qr = login_qr(url);
    // Never show a cropped code: keep the address and pairing code usable on
    // small consoles. A resize restores the complete QR automatically.
    let show_qr =
        !qr.is_empty() && qr[0].width() <= width as usize && qr.len() + 8 <= height as usize;
    if show_qr {
        lines.extend(qr);
        lines.push(Line::raw("Scan to open the page, then enter this code:"));
    } else {
        lines.push(Line::raw("Open the address above and enter this code:"));
    }
    lines.push(Line::styled(
        format!("  {}  ", clean(strval(screen, "code"))),
        Style::default().fg(BG).bg(CORAL).bold(),
    ));
    lines.push(Line::raw("Waiting for approval. Esc cancels."));
    for line in clean(strval(screen, "text")).lines() {
        lines.push(Line::raw(line.to_owned()));
    }
    if !show_qr && url == "https://auth.openai.com/codex/device" {
        lines.push(Line::raw("Enlarge the terminal to show the QR code."));
    }
    lines
}

fn main() -> io::Result<()> {
    let args: Vec<String> = env::args().collect();
    let fd: i32 = args
        .get(1)
        .and_then(|s| s.parse().ok())
        .ok_or(io::Error::other("private UI descriptor required"))?;
    let logfd: i32 = args
        .get(2)
        .and_then(|s| s.parse().ok())
        .ok_or(io::Error::other("private log descriptor required"))?;
    let mut sock = unsafe { UnixStream::from_raw_fd(fd) };
    let reader = sock.try_clone()?;
    let (tx, rx) = mpsc::channel();
    let logtx = tx.clone();
    thread::spawn(move || {
        for line in BufReader::new(reader).lines() {
            match line {
                Ok(l) => {
                    if let Ok(v) = serde_json::from_str::<Value>(&l) {
                        if tx.send(v).is_err() {
                            break;
                        }
                    }
                }
                Err(_) => break,
            }
        }
        let _ = tx.send(json!({"kind":"quit"}));
    });
    thread::spawn(move || {
        let f = unsafe { std::fs::File::from_raw_fd(logfd) };
        for line in BufReader::new(f).lines().map_while(Result::ok) {
            if logtx
                .send(json!({"kind":"log","text":clean(&line)}))
                .is_err()
            {
                break;
            }
        }
    });
    enable_raw_mode()?;
    execute!(io::stdout(), EnterAlternateScreen)?;
    palette(true)?;
    let mut terminal = Terminal::new(CrosstermBackend::new(io::stdout()))?;
    let result = run(&mut terminal, &mut sock, rx);
    let _ = palette(false);
    let _ = disable_raw_mode();
    let _ = execute!(io::stdout(), LeaveAlternateScreen);
    result
}
fn run(
    terminal: &mut Terminal<CrosstermBackend<io::Stdout>>,
    sock: &mut UnixStream,
    rx: mpsc::Receiver<Value>,
) -> io::Result<()> {
    let mut preview_deadline: Option<Instant> = None;
    let mut screen = json!({"kind":"busy","title":"Welcome to OpenClaw","text":"Preparing your system assistant…"});
    let mut logs: VecDeque<String> = VecDeque::new();
    let mut selected = 0usize;
    let mut input = String::new();
    let mut scroll = 0u16;
    let mut context = String::new();
    let mut phase = String::from("Welcome");
    let mut suspended = false;
    let mut help = false;
    let start = Instant::now();
    loop {
        while let Ok(v) = rx.try_recv() {
            match strval(&v, "kind") {
                "quit" => return Ok(()),
                "log" => {
                    for l in strval(&v, "text").lines() {
                        logs.push_back(clean(l));
                    }
                    while logs.len() > 300 {
                        logs.pop_front();
                    }
                }
                "context" => {
                    context = clean(strval(&v, "text"));
                    phase = clean(strval(&v, "phase"));
                }
                "suspend" => {
                    palette(false)?;
                    disable_raw_mode()?;
                    execute!(io::stdout(), LeaveAlternateScreen)?;
                    suspended = true;
                    send(sock, json!({"ok":true,"id":v["id"]}))?;
                }
                "resume" => {
                    palette(true)?;
                    enable_raw_mode()?;
                    execute!(io::stdout(), EnterAlternateScreen)?;
                    terminal.clear()?;
                    suspended = false;
                    send(sock, json!({"ok":true,"id":v["id"]}))?;
                }
                "clear" => {
                    logs.clear();
                }
                _ => {
                    preview_deadline = v["timeout_seconds"]
                        .as_u64()
                        .map(|seconds| Instant::now() + Duration::from_secs(seconds));
                    screen = v;
                    selected = 0;
                    input = String::new();
                    scroll = 0;
                    help = false;
                    if matches!(strval(&screen, "kind"), "busy" | "device") {
                        send(sock, json!({"ok":true,"id":screen["id"]}))?;
                    }
                }
            }
        }
        if suspended {
            thread::sleep(Duration::from_millis(40));
            continue;
        }
        if preview_deadline.is_some_and(|deadline| Instant::now() >= deadline) {
            send(sock, json!({"value":2,"id":screen["id"]}))?;
            preview_deadline = None;
            screen =
                json!({"kind":"busy","title":"Text size","text":"Restoring the previous size…"});
        }
        let kind = strval(&screen, "kind");
        let options = screen["options"].as_array().cloned().unwrap_or_default();
        terminal.draw(|f| {
   let area=f.area();f.render_widget(Block::default().style(Style::default().bg(BG).fg(TEXT)),area);
   if area.width<60 || area.height<18 {f.render_widget(Paragraph::new("OpenClaw\nPlease enlarge this terminal to at least 60 × 18.\nCtrl+C closes setup safely.").wrap(Wrap{trim:false}),area);return}
   let outer=Layout::vertical([Constraint::Length(3),Constraint::Min(10),Constraint::Length(2)]).margin(1).split(area);
   f.render_widget(Paragraph::new(Line::from(vec![Span::styled(" OPENCLAW ",Style::default().fg(CORAL).bold()),Span::styled(" / SYSTEM ASSISTANT",Style::default().fg(MUTED)),Span::raw(format!("    {context}"))])).block(Block::default().borders(Borders::BOTTOM).border_style(Style::default().fg(MUTED))),outer[0]);
   let wide=area.width>=105; let content=if wide {let cols=Layout::horizontal([Constraint::Length(25),Constraint::Min(45)]).spacing(2).split(outer[1]);
     let mut lines:Vec<Line>=CLAW.iter().map(|l|Line::styled(*l,Style::default().fg(CORAL).bold())).collect();
     lines.extend([Line::raw(""),Line::styled(" Your computer.",Style::default().fg(TEXT).bold()),Line::styled(" Your assistant.",Style::default().fg(MUTED)),Line::raw(""),Line::styled(format!("  ● {phase}"),Style::default().fg(MINT)),Line::raw(""),Line::styled(" Guided by OpenClaw",Style::default().fg(MUTED)),Line::styled(" Built by ControlStackAI",Style::default().fg(MUTED))]);
     f.render_widget(Paragraph::new(lines).block(Block::default().style(Style::default().bg(PANEL))).wrap(Wrap{trim:false}),cols[0]); cols[1]
    }else{outer[1]};
   let block=Block::bordered().title(" OPENCLAW ").border_style(Style::default().fg(CORAL)).style(Style::default().bg(PANEL));let inside=block.inner(content);f.render_widget(block,content);
   let controls=if kind=="choose" {options.len().min(8) as u16} else if kind=="input" {3} else {0};
   let details=if matches!(kind,"choose"|"input") {let width=inside.width.max(1) as usize; let rows=clean(strval(&screen,"text")).lines().map(|l|(l.chars().count()/width+1)as u16).sum::<u16>();rows.saturating_add(2).min(inside.height.saturating_sub(controls+3)).max(1)}else{inside.height.saturating_sub(3)};
   let slots=Layout::vertical([Constraint::Length(3),Constraint::Length(details),Constraint::Length(controls),Constraint::Min(0)]).split(inside);
   f.render_widget(Paragraph::new(clean(strval(&screen,"title"))).style(Style::default().fg(TEXT).bold()).wrap(Wrap{trim:false}),slots[0]);
   let inner=slots[1];
   let mut lines=Vec::<Line>::new();
   if help {lines.push(Line::styled("You stay in control",Style::default().fg(MINT).bold()));for l in ["Arrow keys select, Enter continues, Esc goes back.","Page Up / Down scrolls details.","Passwords are hidden. Account approval happens with your provider.","Disk changes require a separate exact confirmation.","The troubleshooting shell is available from the main menu.","Press F1 to return."]{lines.push(Line::raw(l));}}
   else {
    if kind!="device" {for l in clean(strval(&screen,"text")).lines(){lines.push(Line::raw(l.to_string()));}lines.push(Line::raw(""));}
    if kind=="choose" {let items:Vec<ListItem>=options.iter().enumerate().map(|(i,o)|ListItem::new(format!(" {}  {}",i+1,clean(o.as_str().unwrap_or(""))))).collect();let mut state=ListState::default().with_selected(Some(selected));f.render_stateful_widget(List::new(items).highlight_symbol("› ").highlight_style(Style::default().fg(BG).bg(CORAL).bold()),slots[2],&mut state);}
    if kind=="input" {let shown=if screen["secret"].as_bool().unwrap_or(false){"•".repeat(input.chars().count())}else{input.clone()};f.render_widget(Paragraph::new(format!(" › {shown}▏")).style(Style::default().fg(MINT).bold()),slots[2]);}
    if kind=="device" {lines.extend(device_lines(&screen,inner.width,inner.height));}
    if kind=="busy" {let frames=["● ○ ○","○ ● ○","○ ○ ●"];lines.push(Line::styled(frames[(start.elapsed().as_millis()/400%3)as usize],Style::default().fg(MINT)));}
    if kind=="info" {lines.push(Line::styled(" Enter to continue",Style::default().fg(MINT)));}
    if !logs.is_empty() && kind=="busy" && !screen["secret"].as_bool().unwrap_or(false){lines.push(Line::raw(""));lines.push(Line::styled(" RECENT ACTIVITY / REVIEW DETAILS",Style::default().fg(MUTED)));for l in logs.iter().rev().take(40).collect::<Vec<_>>().into_iter().rev(){lines.push(Line::styled(l.clone(),Style::default().fg(MUTED)));}}
   }
   f.render_widget(Paragraph::new(lines).wrap(Wrap{trim:false}).scroll((scroll,0)),inner);
   let footer=if kind=="busy" && !screen["cancellable"].as_bool().unwrap_or(false){" Working — please keep the computer powered on     F1 Help · PgUp/PgDn Details"}else{" ↑↓ Choose · Enter Continue · Esc Back · F1 Help · PgUp/PgDn Details"};
   f.render_widget(Paragraph::new(footer).style(Style::default().fg(MUTED)),outer[2]);
  })?;
        if event::poll(Duration::from_millis(60))? {
            if let Event::Key(k) = event::read()? {
                if k.kind != KeyEventKind::Press {
                    continue;
                }
                if k.code == KeyCode::F(1) {
                    help = !help;
                    continue;
                }
                if k.code == KeyCode::PageDown {
                    scroll = scroll.saturating_add(8);
                    continue;
                }
                if k.code == KeyCode::PageUp {
                    scroll = scroll.saturating_sub(8);
                    continue;
                }
                if help {
                    continue;
                }
                let cancel = k.code == KeyCode::Esc
                    || (k.code == KeyCode::Char('c')
                        && k.modifiers.contains(KeyModifiers::CONTROL));
                if cancel
                    && (matches!(kind, "choose" | "input" | "info")
                        || screen["cancellable"].as_bool().unwrap_or(false))
                {
                    preview_deadline = None;
                    send(sock, json!({"cancel":true}))?;
                    screen =
                        json!({"kind":"busy","title":"Returning","text":"Keeping your choices…"});
                    input.clear();
                    continue;
                }
                match k.code {
                    KeyCode::Up if kind == "choose" => {
                        selected = selected.saturating_sub(1);
                        scroll = 0;
                    }
                    KeyCode::Down if kind == "choose" => {
                        selected = (selected + 1).min(options.len().saturating_sub(1));
                        scroll = 0;
                    }
                    KeyCode::Char(c) if kind == "input" && !c.is_control() => {
                        if input.len() < 4096 {
                            input.push(c);
                        }
                    }
                    KeyCode::Backspace if kind == "input" => {
                        input.pop();
                    }
                    KeyCode::Char(c) if kind == "choose" && c.is_ascii_digit() => {
                        if let Some(n) = c.to_digit(10) {
                            if n > 0 && (n as usize) <= options.len() {
                                selected = n as usize - 1;
                            }
                        }
                    }
                    KeyCode::Enter if matches!(kind, "choose" | "input" | "info") => {
                        let value = if kind == "choose" {
                            json!(selected + 1)
                        } else {
                            json!(input)
                        };
                        preview_deadline = None;
                        send(sock, json!({"value":value,"id":screen["id"]}))?;
                        input.clear();
                        screen = json!({"kind":"busy","title":"OpenClaw","text":"Preparing the next step…"});
                    }
                    _ => {}
                }
            }
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn small_console_keeps_address_and_code_without_cropped_qr() {
        let lines = device_lines(
            &json!({"url":"https://auth.openai.com/codex/device","code":"TEST-CODE"}),
            58,
            12,
        );
        let text = lines
            .iter()
            .map(|line| line.to_string())
            .collect::<Vec<_>>()
            .join("\n");
        assert!(text.contains("https://auth.openai.com/codex/device"));
        assert!(text.contains("TEST-CODE"));
        assert!(text.contains("Enlarge"));
        assert!(!text.contains(['█', '▀', '▄']));
    }
    #[test]
    fn qr_never_encodes_a_token_bearing_or_unrecognized_url() {
        assert!(login_qr("https://auth.openai.com/codex/device?code=SECRET").is_empty());
        assert!(login_qr("https://example.com/").is_empty());
    }
    #[test]
    fn terminal_controls_are_removed() {
        assert_eq!(clean("a\u{1b}\u{07}b\n"), "ab\n");
    }
}
