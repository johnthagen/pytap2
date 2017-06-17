"""Module that wraps the Linux Tun/Tap device."""

from __future__ import absolute_import, division, print_function

import atexit
import enum
import fcntl
import os
import struct


TUNSETIFF = 0x400454ca


@enum.unique
class TapMode(enum.Enum):
    """The device mode.

    Values correlate to corresponding values needed for ioctl calls.
    """

    Tun = 0x0001
    """IFF_TUN."""

    Tap = 0x0002
    """IFF_TAP"""


class TapDevice(object):
    """Tun/Tap device object."""

    def __init__(self, mode=TapMode.Tun, name=None, dev='/dev/net/tun', mtu=1500):
        # type: (TapMode, str, str, int) -> None
        """Initialize TUN/TAP device object.

        Args:
            mode: Select tun or tap device mode.
            name: The name of the new device. If not supplied, a default
                will be provided. An integer will be added to build the real device name.
            dev: The device node name the control channel is connected to.
        """
        self._mode = mode

        # Create interface name to request from tuntap module.
        if name is None:
            if self._mode is TapMode.Tun:
                self._name = 'tun%d'
            elif self._mode is TapMode.Tap:
                self._name = 'tap%d'
        else:
            self._name = name + '%d'

        # Open control device and request interface.
        self._fd = os.open(dev, os.O_RDWR)
        ifs = fcntl.ioctl(self._fd, TUNSETIFF,
                          struct.pack('16sH', self._name.encode(), self._mode.value))

        # Retrieve real interface name from control device.
        self._name = ifs[:16].strip(b'\x00').decode()

        self._mtu = mtu

        # Properly close device on exit.
        atexit.register(self.close)

    @property
    def name(self):
        """The device name."""
        # type: () -> str
        return self._name

    @property
    def mode(self):
        """The device mode (tap or tun)."""
        # type: () -> TapMode
        return self._mode

    @property
    def mtu(self):
        """The device MTU."""
        # type: () -> int
        return self._mtu

    @property
    def fd(self):
        """The device file descriptor.

        Can be used in calls to select().
        """
        # type: () -> int
        return self._fd

    def read(self):
        # type: () -> bytes
        """Read data from the device.

        The device MTU determines how many bytes will be read. The data read from the device
        is returned in its raw form.
        """
        return os.read(self._fd, self._mtu)

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
        ifconfig_cmd = 'ifconfig {} '.format(self._name)

        try:
            ifconfig_cmd = '{} {} '.format(ifconfig_cmd, args['address'])
        except KeyError:
            pass

        try:
            ifconfig_cmd = '{} {} {} '.format(ifconfig_cmd, 'netmask', args['netmask'])
        except KeyError:
            pass

        try:
            ifconfig_cmd = '{} {} {} '.format(ifconfig_cmd, 'network', args['network'])
        except KeyError:
            pass

        try:
            ifconfig_cmd = '{} {} {} '.format(ifconfig_cmd, 'broadcast', args['broadcast'])
        except KeyError:
            pass

        try:
            ifconfig_cmd = '{} {} {} '.format(ifconfig_cmd, 'mtu', args['mtu'])
        except KeyError:
            pass

        try:
            ifconfig_cmd = '{} {} {} {} '.format(ifconfig_cmd, 'hw', args['hwclass'],
                                                 args['hwaddress'])
        except KeyError:
            pass

        ret = os.system(ifconfig_cmd)

        if ret != 0:
            raise IfconfigError('ifconfig command failed.')

        # Save MTU if ifconfig was successful so buffer sizes can be adjusted.
        try:
            self._mtu = args['mtu']
        except KeyError:
            pass

    def up(self):
        # type: () -> None
        """Bring up device. This will effectively run "ifconfig up" on the device."""
        ret = os.system('ifconfig {} up'.format(self._name))

        if ret != 0:
            raise IfconfigError()

    def down(self):
        # type: () -> None
        """Bring down device. This will effectively call "ifconfig down" on the device."""
        ret = os.system('ifconfig {} down'.format(self._name))

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
