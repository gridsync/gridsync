# -*- mode: ruby -*-
# vi: set ft=ruby :

# Needed for copying NVRAM file for macos-11 as per https://app.vagrantup.com/amarcireau/boxes/macos
ENV["VAGRANT_EXPERIMENTAL"] = "typed_triggers"

def update_macos
  return <<-EOF
    softwareupdate --verbose --install --all --restart
  EOF
end


def gnome_desktop
  return <<-EOF
    yum -y update
    yum -y groupinstall "GNOME Desktop"
    yum clean all
    systemctl enable gdm
    sh -c 'echo -e "[daemon]\nAutomaticLogin=vagrant\nAutomaticLoginEnable=True" > /etc/gdm/custom.conf'
    systemctl set-default graphical.target
    systemctl isolate graphical.target
  EOF
end


def ubuntu_desktop
  return <<-EOF
    apt-get -y -qq update
    apt-get -y -qq dist-upgrade
    apt-get -y -qq install ubuntu-desktop
    apt-get autoremove
    apt-get clean
    sh -c 'echo "[daemon]\nAutomaticLogin=vagrant\nAutomaticLoginEnable=True" > /etc/gdm3/custom.conf'
    systemctl set-default graphical.target
    systemctl isolate graphical.target
  EOF
end


def test
  return <<-EOF
    rm -rf ~/gridsync
    cp -R ~/vagrant ~/gridsync
    cd ~/gridsync
    CI=true make clean test
  EOF
end


def test_windows
  return <<-EOF
    git config --global core.autocrlf false
    cd ~
    rm -r -fo .\\gridsync -erroraction "silentlycontinue"
    cp -R .\\vagrant .\\gridsync
    cd .\\gridsync
    $env:CI = "true"
    gci env:
    .\\make.bat clean
    .\\make.bat test
    ls
  EOF
end


def make
  return <<-EOF
    rm -rf ~/gridsync
    cp -R ~/vagrant ~/gridsync
    cd ~/gridsync
    CI=true make clean all
  EOF
end


def make_windows
  return <<-EOF
    git config --global core.autocrlf false
    cd ~
    rm -r -fo .\\gridsync -erroraction "silentlycontinue"
    cp -R .\\vagrant .\\gridsync
    cd .\\gridsync
    $env:CI = "true"
    gci env:
    .\\make.bat clean
    .\\make.bat
    ls
  EOF
end


Vagrant.configure("2") do |config|
  config.vm.boot_timeout = 600
  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.vm.provider "virtualbox" do |vb|
    vb.gui = true
    vb.memory = "4096"
    vb.cpus = 2
    vb.customize ["modifyvm", :id, "--usb", "on"]
  end

  config.vm.define "centos-7" do |b|
    b.vm.box = "centos/7"
    b.vm.hostname = "centos-7"
    b.vm.synced_folder ".", "/home/vagrant/vagrant", type: "rsync"
    b.vm.provision "desktop", type: "shell", inline: gnome_desktop
    b.vm.provision "devtools", type: "shell", privileged: false, run: "never", env: {"SKIP_DOCKER_INSTALL": "1"}, path: "scripts/provision_devtools.sh"
    b.vm.provision "test", type: "shell", privileged: false, run: "never", inline: test
    b.vm.provision "build", type: "shell", privileged: false, run: "never", inline: make
    b.vm.provision "buildbot-worker", type: "shell", privileged: false, run: "never", env: {"BUILDBOT_HOST": "#{ENV['BUILDBOT_HOST']}", "BUILDBOT_NAME": "#{ENV['BUILDBOT_NAME']}", "BUILDBOT_PASS": "#{ENV['BUILDBOT_PASS']}"}, path: "scripts/provision_buildbot-worker.sh"
  end

  config.vm.define "ubuntu-18.04" do |b|
    b.vm.box = "ubuntu/bionic64"
    b.vm.hostname = "ubuntu-18.04"
    b.vm.synced_folder ".", "/home/vagrant/vagrant"
    b.vm.provision "desktop", type: "shell", inline: ubuntu_desktop
    b.vm.provision "devtools", type: "shell", privileged: false, run: "never", path: "scripts/provision_devtools.sh"
    b.vm.provision "test", type: "shell", privileged: false, run: "never", inline: test
    b.vm.provision "build", type: "shell", privileged: false, run: "never", inline: make
    b.vm.provision "buildbot-worker", type: "shell", privileged: false, run: "never", env: {"BUILDBOT_HOST": "#{ENV['BUILDBOT_HOST']}", "BUILDBOT_NAME": "#{ENV['BUILDBOT_NAME']}", "BUILDBOT_PASS": "#{ENV['BUILDBOT_PASS']}"}, path: "scripts/provision_buildbot-worker.sh"
  end

  config.vm.define "ubuntu-20.04" do |b|
    b.vm.box = "ubuntu/focal64"
    b.vm.hostname = "ubuntu-20.04"
    b.vm.synced_folder ".", "/home/vagrant/vagrant", type: "rsync"
    b.vm.provision "desktop", type: "shell", inline: ubuntu_desktop
    b.vm.provision "devtools", type: "shell", privileged: false, run: "never", path: "scripts/provision_devtools.sh"
    b.vm.provision "test", type: "shell", privileged: false, run: "never", inline: test
    b.vm.provision "build", type: "shell", privileged: false, run: "never", inline: make
    b.vm.provision "buildbot-worker", type: "shell", privileged: false, run: "never", env: {"BUILDBOT_HOST": "#{ENV['BUILDBOT_HOST']}", "BUILDBOT_NAME": "#{ENV['BUILDBOT_NAME']}", "BUILDBOT_PASS": "#{ENV['BUILDBOT_PASS']}"}, path: "scripts/provision_buildbot-worker.sh"
  end

  config.vm.define "ubuntu-22.04" do |b|
    b.vm.box = "ubuntu/jammy64"
    b.vm.hostname = "ubuntu-22.04"
    b.vm.synced_folder ".", "/home/vagrant/vagrant", type: "rsync"
    b.vm.provision "desktop", type: "shell", inline: ubuntu_desktop
    b.vm.provision "devtools", type: "shell", privileged: false, run: "never", path: "scripts/provision_devtools.sh"
    b.vm.provision "test", type: "shell", privileged: false, run: "never", inline: test
    b.vm.provision "build", type: "shell", privileged: false, run: "never", inline: make
    b.vm.provision "buildbot-worker", type: "shell", privileged: false, run: "never", env: {"BUILDBOT_HOST": "#{ENV['BUILDBOT_HOST']}", "BUILDBOT_NAME": "#{ENV['BUILDBOT_NAME']}", "BUILDBOT_PASS": "#{ENV['BUILDBOT_PASS']}"}, path: "scripts/provision_buildbot-worker.sh"
  end

  config.vm.define "macos-11" do |b|
    b.vm.box = "amarcireau/macos"
    b.vm.hostname = "macos-11"
    b.vm.box_version = "11.6.8"
    b.vm.provider "virtualbox" do |vb|
      # Guest additions are not supported by Big Sur guests
      # See https://app.vagrantup.com/amarcireau/boxes/macos
      vb.check_guest_additions = false
      vb.customize ["modifyvm", :id, "--usbehci", "off"]
      vb.customize ["modifyvm", :id, "--usbxhci", "off"]
      vb.customize ["setextradata", :id, "VBoxInternal/Devices/efi/0/Config/DmiSystemProduct", "MacBookPro11,3"]
      vb.customize ["setextradata", :id, "VBoxInternal/Devices/efi/0/Config/DmiSystemVersion", "1.0"]
      vb.customize ["setextradata", :id, "VBoxInternal/Devices/efi/0/Config/DmiBoardProduct", "Iloveapple"]
      vb.customize ["setextradata", :id, "VBoxInternal/Devices/smc/0/Config/DeviceKey", "ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc"]
    end
    # "The NVRAM file packaged with this Vagrant box must be copied manually after importing it into Virtualbox."
    # See https://app.vagrantup.com/amarcireau/boxes/macos
    b.trigger.after :"VagrantPlugins::ProviderVirtualBox::Action::Import", type: :action do |t|
        t.ruby do |env, machine|
            FileUtils.cp(
                machine.box.directory.join("include").join("macOS.nvram").to_s,
                machine.provider.driver.execute_command(["showvminfo", machine.id, "--machinereadable"]).
                    split(/\n/).
                    map {|line| line.partition(/=/)}.
                    select {|partition| partition.first == "BIOS NVRAM File"}.
                    last.
                    last[1..-2]
            )
        end
    end
    # Shared directories are not supported by Big Sur guests
    # See https://app.vagrantup.com/amarcireau/boxes/macos
    b.vm.synced_folder ".", "/Users/vagrant/vagrant", disabled: true
    b.vm.provision "update", type: "shell", privileged: false, run: "never", inline: update_macos
    b.vm.provision "devtools", type: "shell", privileged: false, run: "never", path: "scripts/provision_devtools.sh"
    b.vm.provision "test", type: "shell", privileged: false, run: "never", inline: test
    b.vm.provision "build", type: "shell", privileged: false, run: "never", inline: make
    b.vm.provision "buildbot-worker", type: "shell", privileged: false, run: "never", env: {"BUILDBOT_HOST": "#{ENV['BUILDBOT_HOST']}", "BUILDBOT_NAME": "#{ENV['BUILDBOT_NAME']}", "BUILDBOT_PASS": "#{ENV['BUILDBOT_PASS']}"}, path: "scripts/provision_buildbot-worker.sh"
  end

  config.vm.define "macos-12" do |b|
    b.vm.box = "amarcireau/macos"
    b.vm.hostname = "macos-12"
    b.vm.box_version = "12.5"
    b.vm.provider "virtualbox" do |vb|
      # Guest additions are not supported by Big Sur guests
      # See https://app.vagrantup.com/amarcireau/boxes/macos
      vb.check_guest_additions = false
      vb.customize ["modifyvm", :id, "--usbehci", "off"]
      vb.customize ["modifyvm", :id, "--usbxhci", "off"]
      vb.customize ["setextradata", :id, "VBoxInternal/Devices/efi/0/Config/DmiSystemProduct", "MacBookPro11,3"]
      vb.customize ["setextradata", :id, "VBoxInternal/Devices/efi/0/Config/DmiSystemVersion", "1.0"]
      vb.customize ["setextradata", :id, "VBoxInternal/Devices/efi/0/Config/DmiBoardProduct", "Iloveapple"]
      vb.customize ["setextradata", :id, "VBoxInternal/Devices/smc/0/Config/DeviceKey", "ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc"]
    end
    # "The NVRAM file packaged with this Vagrant box must be copied manually after importing it into Virtualbox."
    # See https://app.vagrantup.com/amarcireau/boxes/macos
    b.trigger.after :"VagrantPlugins::ProviderVirtualBox::Action::Import", type: :action do |t|
        t.ruby do |env, machine|
            FileUtils.cp(
                machine.box.directory.join("include").join("macOS.nvram").to_s,
                machine.provider.driver.execute_command(["showvminfo", machine.id, "--machinereadable"]).
                    split(/\n/).
                    map {|line| line.partition(/=/)}.
                    select {|partition| partition.first == "BIOS NVRAM File"}.
                    last.
                    last[1..-2]
            )
        end
    end
    # Shared directories are not supported by Big Sur guests
    # See https://app.vagrantup.com/amarcireau/boxes/macos
    b.vm.synced_folder ".", "/Users/vagrant/vagrant", disabled: true
    b.vm.provision "update", type: "shell", privileged: false, run: "never", inline: update_macos
    b.vm.provision "devtools", type: "shell", privileged: false, run: "never", path: "scripts/provision_devtools.sh"
    b.vm.provision "test", type: "shell", privileged: false, run: "never", inline: test
    b.vm.provision "build", type: "shell", privileged: false, run: "never", inline: make
    b.vm.provision "buildbot-worker", type: "shell", privileged: false, run: "never", env: {"BUILDBOT_HOST": "#{ENV['BUILDBOT_HOST']}", "BUILDBOT_NAME": "#{ENV['BUILDBOT_NAME']}", "BUILDBOT_PASS": "#{ENV['BUILDBOT_PASS']}"}, path: "scripts/provision_buildbot-worker.sh"
  end

  config.vm.define "windows-10" do |b|
    b.vm.box = "gusztavvargadr/windows-10"
    b.vm.hostname = "windows-10"
    b.winrm.transport = :plaintext
    b.winrm.basic_auth_only = true 
    b.vm.provider "virtualbox" do |vb|
      vb.customize ['modifyvm', :id, '--usb', 'on']
      vb.customize ['usbfilter', 'add', '0',
        '--target', :id,
        '--name', "SafeNet Token JC [0001]",
        '--manufacturer', "SafeNet",
        '--vendorid', "0x0529",
        '--productid', "0x0620",
        '--product', "Token JC"]
    end
    b.vm.synced_folder ".", "/Users/vagrant/vagrant"
    b.vm.provision "devtools", type: "shell", run: "never", path: "scripts/provision_devtools.bat"
    b.vm.provision "test", type: "shell", run: "never", inline: test_windows
    b.vm.provision "build", type: "shell", run: "never", inline: make_windows
    b.vm.provision "buildbot-worker", type: "shell", privileged: false, run: "never", env: {"BUILDBOT_HOST": "#{ENV['BUILDBOT_HOST']}", "BUILDBOT_NAME": "#{ENV['BUILDBOT_NAME']}", "BUILDBOT_PASS": "#{ENV['BUILDBOT_PASS']}"}, path: "scripts/provision_buildbot-worker.ps1"
    b.vm.provision "sac", type: "shell", run: "never", path: "scripts/provision_sac.ps1"
  end

  config.vm.define "windows-11" do |b|
    b.vm.box = "gusztavvargadr/windows-11"
    b.vm.hostname = "windows-11"
    b.winrm.transport = :plaintext
    b.winrm.basic_auth_only = true 
    b.vm.provider "virtualbox" do |vb|
      vb.customize ['modifyvm', :id, '--usb', 'on']
      vb.customize ['usbfilter', 'add', '0',
        '--target', :id,
        '--name', "SafeNet Token JC [0001]",
        '--manufacturer', "SafeNet",
        '--vendorid', "0x0529",
        '--productid', "0x0620",
        '--product', "Token JC"]
    end
    b.vm.synced_folder ".", "/Users/vagrant/vagrant"
    b.vm.provision "devtools", type: "shell", run: "never", path: "scripts/provision_devtools.bat"
    b.vm.provision "test", type: "shell", run: "never", inline: test_windows
    b.vm.provision "build", type: "shell", run: "never", inline: make_windows
    b.vm.provision "buildbot-worker", type: "shell", privileged: false, run: "never", env: {"BUILDBOT_HOST": "#{ENV['BUILDBOT_HOST']}", "BUILDBOT_NAME": "#{ENV['BUILDBOT_NAME']}", "BUILDBOT_PASS": "#{ENV['BUILDBOT_PASS']}"}, path: "scripts/provision_buildbot-worker.ps1"
    b.vm.provision "sac", type: "shell", run: "never", path: "scripts/provision_sac.ps1"
  end

end
