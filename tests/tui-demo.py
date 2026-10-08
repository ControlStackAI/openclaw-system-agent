"""Non-secret console fixture. Runs only in the isolated TUI VM."""
from system_agent.tui import Interface, Cancelled
from system_agent.console_font import initialize, choose_size
initialize()
with Interface(True,'nixos') as ui:
 while True:
  try:
   choice=ui.choose('Welcome to your OpenClaw System Assistant',[
    'Connect your AI account','Choose your desktop','Try protected input','Review a disk plan','Text size','Leave setup'])
   if choice==1:
    ui.context('Connect your AI account')
    ui.request({'kind':'device','title':'Connect your ChatGPT account','text':'On your phone or another computer, visit this address.\nThis is a synthetic demonstration; no real account is used.',
                'url':'https://auth.openai.com/codex/device','code':'TEST-CODE','cancellable':True})
    import time
    while True:ui.cancelled();time.sleep(.1)
   elif choice==2:
    ui.choose('Which desktop would you like?',['Hyprland + Quickshell — tiling windows and compact islands','GNOME — simple activities and applications','KDE Plasma — familiar menus and flexible settings','No desktop — local text console'])
   elif choice==3:
    value=ui.input('Enter a test password',True)
    assert value=='fixturepassword'
    ui.info('Protected input accepted','The password did not enter the conversation or logs.')
   elif choice==4:
    ui.notes='Disk: EXAMPLE 48 GiB — serial DEMO123\nAll contents of this disk will be lost.\nLayout: EFI startup partition and ZFS datasets.\nSnapshots need an independent backup.\nNo operation will run in this fixture.'
    value=ui.input('Type ERASE DEMO123 to confirm this example')
    ui.info('Review complete','This fixture did not change any disk.')
   elif choice==5:
    choose_size(ui)
   else:break
  except Cancelled:pass
