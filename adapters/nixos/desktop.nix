{ desktop }:
assert builtins.elem desktop [ "none" "plasma" "gnome" "hyprland" ];
{
  imports = if desktop == "hyprland" then [ ./hyprland ] else [ ];
  services.desktopManager.plasma6.enable = desktop == "plasma";
  services.displayManager.sddm.enable = builtins.elem desktop [ "plasma" "hyprland" ];
  services.desktopManager.gnome.enable = desktop == "gnome";
  services.displayManager.gdm.enable = desktop == "gnome";
}
