{ desktop }:
assert builtins.elem desktop [ "none" "plasma" "gnome" ];
{
  services.desktopManager.plasma6.enable = desktop == "plasma";
  services.displayManager.sddm.enable = desktop == "plasma";
  services.desktopManager.gnome.enable = desktop == "gnome";
  services.displayManager.gdm.enable = desktop == "gnome";
}
