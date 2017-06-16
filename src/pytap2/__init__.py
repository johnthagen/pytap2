"""Module that wraps the Linux TUN/TAP device."""

from __future__ import absolute_import, division, print_function

import atexit
import fcntl
import os
import struct

TUNSETIFF = 0x400454ca

IFF_TUN = 0x0001
IFF_TAP = 0x0002


class TapDevice(object):
    """ TUN/TAP device object """

    def __init__(self, mode=IFF_TUN, name='', dev='/dev/net/tun', mtu=1500):
        # type: (int, str, str, int) -> None
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
        ifs = fcntl.ioctl(fd, TUNSETIFF, struct.pack('16sH', self.name.encode(), self.mode))

        # Retrieve real interface name from control device.
        self.name = ifs[:16].strip(b'\x00').decode()

        # Set default MTU.
        self.mtu = mtu

        # Store fd for later.
        self._fd = fd

        # Properly close device on exit.
        atexit.register(self.close)

    def read(self):
        # type: () -> bytes
        """Read data from the device.

        The device mtu determines how many bytes will be read. The data read from the device
        is returned in its raw form.
        """
        return os.read(self._fd, self.mtu)

    def write(self, data):
        # type: (bytes) -> None
        """Write data to the device. No care is taken for MTU limitations or similar."""
        os.write(self._fd, data)

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
        # TODO: New systems like Ubuntu 17.04 do not come with ifconfig pre-installed.
        ifconfig_cmd = 'ifconfig ' + self.name + ' '

        try:
            ifconfig_cmd = ifconfig_cmd + args['address'] + ' '
        except KeyError:
            pass

        try:
            ifconfig_cmd = ifconfig_cmd + 'netmask ' + args['netmask'] + ' '
        except KeyError:
            pass

        try:
            ifconfig_cmd = ifconfig_cmd + 'network ' + args['network'] + ' '
        except KeyError:
            pass

        try:
            ifconfig_cmd = ifconfig_cmd + 'broadcast ' + args['broadcast'] + ' '
        except KeyError:
            pass

        try:
            ifconfig_cmd = ifconfig_cmd + 'mtu ' + str(args['mtu']) + ' '
        except KeyError:
            pass

        try:
            ifconfig_cmd = ifconfig_cmd + 'hw ' + args['hwclass'] + ' ' + args['hwaddress'] + ' '
        except KeyError:
            pass

        ret = os.system(ifconfig_cmd)

        if ret != 0:
            raise IfconfigError('ifconfig command failed.')

        # Save MTU if ifconfig was successful so buffer sizes can be adjusted.
        try:
            self.mtu = args['mtu']
        except KeyError:
            pass

    def up(self):
        # type: () -> None
        """Bring up device. This will effectively run "ifconfig up" on the device."""
        ret = os.system('ifconfig ' + self.name + ' up')

        if ret != 0:
            raise IfconfigError()

    def down(self):
        # type: () -> None
        """Bring down device. This will effectively call "ifconfig down" on the device."""
        ret = os.system('ifconfig ' + self.name + ' down')

        if ret != 0:
            raise IfconfigError()

    def close(self):
        # type: () -> None
        """Close the control channel.

        This will effectively drop all locks and remove the TUN/TAP device.

        You must manually take care that your code does not try to operate on the interface
        after closing the control channel.
        """
        os.close(self._fd)


class IfconfigError(Exception):
    """Exception thrown if an ifconfig command returns with a non-zero exit status."""
