"""Module that wraps the Linux TUN/TAP device."""

import atexit
import fcntl
import os
import struct


TUNSETIFF = 0x400454ca
IFF_TUN = 0x0001
IFF_TAP = 0x0002


class TapDevice(object):
    """ TUN/TAP device object """

    DEFAULT_MTU = 1500

    def __init__(self, mode=IFF_TUN, name='', dev='/dev/net/tun'):
        """Initialize TUN/TAP device object.

        Args:
            mode: Either IFF_TUN or IFF_TAP to select tun or tap device mode.
            name: The name of the new device. An integer will be added to
                build the real device name.
            dev: The device node name the control channel is connected to.
        """
        # Set interface mode in object.
        self.mode = mode

        # Create interface name to request from tuntap module.
        if name == '':
            if self.mode == IFF_TUN:
                self.name = 'tun%d'
            elif self.mode == IFF_TAP:
                self.name = 'tap%d'
        elif name.endswith('%d'):
            self.name = name
        else:
            self.name = name + '%d'

        # Open control device and request interface.
        fd = os.open(dev, os.O_RDWR)
        ifs = fcntl.ioctl(fd, TUNSETIFF, struct.pack('16sH', self.name, self.mode))

        # Retrieve real interface name from control device.
        self.name = ifs[:16].strip('\x00')

        # Set default MTU.
        self.mtu = self.DEFAULT_MTU

        # Store fd for later.
        self.__fd__ = fd

        # Properly close device on exit.
        atexit.register(self.close)

    def read(self):
        """Read data from the device.

        The device mtu determines how many bytes will be read. The data read from the device
        is returned in its raw form.
        """

        data = os.read(self.__fd__, self.mtu)
        return data

    def write(self, data):
        """Write data to the device. No care is taken for MTU limitations or similar."""
        os.write(self.__fd__, data)

    def ifconfig(self, **args):
        """Issue ifconfig command on the device.

        Keyword Args:
            address: IP address of the device, can be in CIDR notation (see man ifconfig).
            netmask: Network mask.
            network: Network base address, normally set automatically.
            broadcast: Broadcast address, normally set automatically.
            mtu: Link MTU, this will also affect the read() method.
            hwclass: Hardware class, normally ether for ethernet.
            hwaddress: Hardware (MAC) address, in conjunction with hwclass.
        """
        ifconfig = 'ifconfig ' + self.name + ' '

        # IP address ?
        try:
            ifconfig = ifconfig + args['address'] + ' '
        except KeyError:
            pass

        # Network mask ?
        try:
            ifconfig = ifconfig + 'netmask ' + args['netmask'] + ' '
        except KeyError:
            pass

        # Network base address ?
        try:
            ifconfig = ifconfig + 'network ' + args['network'] + ' '
        except KeyError:
            pass

        # Broadcast address ?
        try:
            ifconfig = ifconfig + 'broadcast ' + args['broadcast'] + ' '
        except KeyError:
            pass

        # MTU ?
        try:
            ifconfig = ifconfig + 'mtu ' + str(args['mtu']) + ' '
        except KeyError:
            pass

        # Hardware address ?
        try:
            ifconfig = ifconfig + 'hw ' + args['hwclass'] + ' ' + args['hwaddress'] + ' '
        except KeyError:
            pass

        # Try to set off ifconfig command
        ret = os.system(ifconfig)

        if ret != 0:
            raise IfconfigError()

        # Save MTU if ifconfig was successful so buffer sizes can be adjusted.
        try:
            self.mtu = args['mtu']
        except KeyError:
            pass

    def up(self):
        """Bring up device. This will effectively run "ifconfig up" on the device."""
        ret = os.system('ifconfig ' + self.name + ' up')

        if ret != 0:
            raise IfconfigError()

    def down(self):
        """Bring down device. This will effectively call "ifconfig down" on the device."""
        ret = os.system('ifconfig ' + self.name + ' down')

        if ret != 0:
            raise IfconfigError()

    def close(self):
        """Close the control channel.

        This will effectively drop all locks and remove the TUN/TAP device.

        You must manually take care that your code does not try to operate on the interface
        after closing the control channel.
        """
        os.close(self.__fd__)


class IfconfigError(Exception):
    """Exception thrown if an ifconfig command returns with a non-zero exit status."""
