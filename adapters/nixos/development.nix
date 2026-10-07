# General development tools. Project-specific versions belong in nix develop shells.
{ pkgs, lib, ... }: {
  programs.neovim = { enable = true; defaultEditor = true; viAlias = true; vimAlias = true; };
  environment.variables = { EDITOR = "nvim"; VISUAL = "nvim"; };
  programs.git = { enable = true; lfs.enable = true; };
  programs.direnv = { enable = true; nix-direnv.enable = true; };
  virtualisation.podman = { enable = true; defaultNetwork.settings.dns_enabled = true; };
  environment.systemPackages = with pkgs; [
    gh delta ripgrep fd fzf jq yq-go bat eza tmux btop tree
    curl wget openssl unzip zip p7zip
    gcc gnumake cmake ninja pkg-config gdb
    python3 uv nodejs_24 pnpm go rustc cargo
    shellcheck shfmt nixd nixfmt
    podman-compose qemu_kvm virtiofsd
  ];
  programs.neovim.configure.customLuaRC = ''
    vim.opt.number = true
    vim.opt.relativenumber = true
    vim.opt.mouse = "a"
    vim.opt.termguicolors = true
    vim.opt.signcolumn = "yes"
    vim.opt.expandtab = true
    vim.opt.shiftwidth = 4
    vim.opt.tabstop = 4
    vim.opt.ignorecase = true
    vim.opt.smartcase = true
    vim.opt.undofile = true
    vim.g.mapleader = " "
    vim.cmd.colorscheme("habamax")
    -- Keep the owner’s normal customization path available after our defaults.
    local user_init = vim.fn.stdpath("config") .. "/init.lua"
    if vim.fn.filereadable(user_init) == 1 then dofile(user_init) end
  '';
  xdg.mime.defaultApplications."text/plain" = "nvim.desktop";
}
