-- Test-only binding: proves native Lua executes in the logged-in session.
hl.bind("SUPER + F9", hl.dsp.exec_cmd("touch /home/owner/lua-shortcut-worked"))
