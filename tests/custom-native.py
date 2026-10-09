"""Guest-only native install fixture. Never run on a host or physical disk."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path('/mnt/controlstack-custom')
def run(*args, **kw):
    return subprocess.run(list(args), check=True, text=True, **kw)

def output(*args):
    return subprocess.check_output(list(args), text=True).strip()

def main(distro):
    assert os.geteuid() == 0
    assert output('cat','/sys/class/dmi/id/product_name') in ('Standard PC (Q35 + ICH9, 2009)', 'KVM')
    assert output('lsblk','-dn','-o','SERIAL','/dev/vda') == 'CONTROLSTACK-VM-ONLY'
    assert int(output('blockdev','--getsize64','/dev/vda')) == 48 * 1024**3
    assert Path('/etc/agent-installer/live-image').exists()
    record = json.loads(Path('/run/controlstack-agent/lifecycle/custom-deployment.json').read_text())
    assert record['state'] == 'preparing' and record['disk_erasure_approved']
    assert record['plan']['disk'] == '/dev/vda'
    assert record['plan']['storage_action'] == 'erase'
    assert record['plan']['storage_plan'].startswith('VM fixture:')
    assert not ROOT.is_symlink() and not os.path.ismount(ROOT)
    # Public system paths must remain readable/traversable after boot.
    # Protected account input is handled separately by the local console.
    os.umask(0o022)
    ROOT.mkdir(exist_ok=True)
    inputs = json.loads(Path('/etc/controlstack-agent/' + ('arch-target.json' if distro == 'arch' else 'install-inputs.json')).read_text())
    run('sgdisk','--zap-all','--new=1:0:+1G','--typecode=1:EF00','--new=2:0:0','--typecode=2:8300','/dev/vda')
    run('partprobe','/dev/vda'); run('udevadm','settle')
    run('mkfs.fat','-F','32','/dev/vda1'); run('mkfs.ext4','-F','/dev/vda2')
    run('mount','-t','ext4','/dev/vda2',str(ROOT)); (ROOT/'boot').mkdir()
    run('mount','-t','vfat','/dev/vda1',str(ROOT/'boot'))
    root_uuid=output('blkid','-s','UUID','-o','value','/dev/vda2')
    esp_uuid=output('blkid','-s','UUID','-o','value','/dev/vda1')
    if distro == 'arch':
        # Native package bootstrap, not the preset's full desktop payload.
        packages='base linux linux-firmware intel-ucode amd-ucode mkinitcpio networkmanager wpa_supplicant sudo python whois neovim'.split()
        run('pacstrap','-K','-C','/etc/pacman.conf',str(ROOT),*packages)
        run('cp','/etc/pacman.conf',str(ROOT/'etc/pacman.conf'))
        (ROOT/'nix').mkdir(exist_ok=True); run('cp','-a','/nix/.',str(ROOT/'nix'))
        (ROOT/'opt').mkdir(exist_ok=True); run('cp','-a','/opt/codex',str(ROOT/'opt'))
        from adapters.arch.target import configure, write
        choices=dict(username='owner',desktop='none',hostname='vmcustom',locale='en_US.UTF-8',
                     keyboard='us',timezone='UTC',power_policy='standard',login_policy='password')
        configure(ROOT,inputs['runtime'],choices)
        write(ROOT,'etc/machine-id',uuid.uuid4().hex+'\n')
        write(ROOT,'etc/fstab',f'UUID={root_uuid} / ext4 defaults 0 1\nUUID={esp_uuid} /boot vfat umask=0077 0 2\n')
        def chroot(*a): return run('arch-chroot',str(ROOT),*a)
        chroot('groupadd','--system','controlstack-agent')
        chroot('useradd','--system','--gid','controlstack-agent','--home-dir','/var/lib/controlstack-agent','--shell','/usr/bin/nologin','controlstack-agent')
        chroot('useradd','-m','-G','wheel','owner'); chroot('passwd','-l','root')
        chroot('locale-gen')
        write(ROOT,'etc/mkinitcpio.conf','MODULES=(virtio_pci virtio_blk ahci nvme xhci_pci)\nHOOKS=(base udev modconf keyboard block filesystems fsck)\nCOMPRESSION=zstd\n')
        kernel=inputs['kernel_release']
        run('cp',str(ROOT/'usr/lib/modules'/kernel/'vmlinuz'),str(ROOT/'boot/vmlinuz-linux'))
        chroot('mkinitcpio','-k',kernel,'-g','/boot/initramfs-linux.img')
        chroot('bootctl','--esp-path=/boot','--no-variables','install')
        write(ROOT,'boot/loader/loader.conf','default custom.conf\ntimeout 2\n')
        write(ROOT,'boot/loader/entries/custom.conf',f'title Custom Arch console\nlinux /vmlinuz-linux\ninitrd /initramfs-linux.img\noptions root=UUID={root_uuid} rw console=ttyS0,115200 console=tty0\n')
        chroot('systemctl','enable','NetworkManager','systemd-timesyncd','controlstack-agent','controlstack-agent-boot-check')
        # Do not start resident services inside the target before finalization.
        run('arch-chroot',str(ROOT),'pacman','-Q',stdout=(ROOT/'etc/controlstack-agent/packages.txt').open('w'))
    else:
        q=json.dumps
        expression=f'''import {q(inputs['nixpkgs']+'/nixos')} {{
          system="x86_64-linux";
          configuration={{pkgs, ...}}: {{
            imports=[ {q(inputs['source']+'/adapters/nixos/module.nix')} {q(inputs['source']+'/adapters/nixos/networking.nix')} ];
            services.controlstackAgent={{ enable=true; mutableProviderSetup=true; workspaceExecution=true;
              package=builtins.storePath {q(inputs['runtime'])}; corePackage=builtins.storePath {q(inputs['core'])}; }};
            boot.loader.systemd-boot.enable=true; boot.loader.efi.canTouchEfiVariables=false;
            boot.initrd.availableKernelModules=["virtio_pci" "virtio_blk" "ahci" "nvme" "xhci_pci"];
            boot.kernelParams=["console=ttyS0,115200" "console=tty0"];
            hardware.enableRedistributableFirmware=true;
            networking.hostName="vmcustom"; services.timesyncd.enable=true;
            users.users.owner={{isNormalUser=true; extraGroups=["wheel"]; hashedPasswordFile="/var/lib/controlstack-owner.password";}};
            fileSystems."/"={{device="/dev/disk/by-uuid/{root_uuid}";fsType="ext4";}};
            fileSystems."/boot"={{device="/dev/disk/by-uuid/{esp_uuid}";fsType="vfat";}};
            environment.etc."controlstack-agent/custom-inputs.json".text=builtins.toJSON {{
              nixpkgs=builtins.storePath {q(inputs['nixpkgs'])}; source=builtins.storePath {q(inputs['source'])}; }};
            system.stateVersion="26.05";
          }};
        }}'''
        (ROOT/'etc/nixos').mkdir(parents=True)
        (ROOT/'etc').chmod(0o755); (ROOT/'etc/nixos').chmod(0o755)
        (ROOT/'etc/nixos/custom.nix').write_text(expression)
        (ROOT/'var/lib').mkdir(parents=True); (ROOT/'var').chmod(0o755); (ROOT/'var/lib').chmod(0o755); (ROOT/'var/lib/controlstack-owner.password').write_text('!\n')
        (ROOT/'var/lib/controlstack-owner.password').chmod(0o600)
        (ROOT/'etc/machine-id').write_text(uuid.uuid4().hex+'\n')
        (ROOT/'etc/machine-id').chmod(0o444)
        system=output('nix-build',str(ROOT/'etc/nixos/custom.nix'),'-A','config.system.build.toplevel','--no-out-link','--max-jobs','2','--cores','2')
        run('nixos-install','--root',str(ROOT),'--system',system,'--no-root-passwd','--no-channel-copy')
    print('CUSTOM_NATIVE_FILES_READY',flush=True)

if __name__ == '__main__': main(sys.argv[1])
