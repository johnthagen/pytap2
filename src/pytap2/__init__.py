"""Module that wraps the Linux Tun/Tap device."""

import atexit
import enum
import fcntl
import os
import struct

TUNSETIFF = 0x400454ca

IFF_NO_PI = 0x1000
"""Mask to disable packet information from being prepended to packets sent through TUN/TAP."""

PACKET_INFO_SIZE = 4
"""Size of packet information, in bytes, prepended to packets sent in TUN/TAP when packet
information is enabled."""


@enum.unique
class TapMode(enum.Enum):
    """The device mode.

    Values correlate to corresponding values needed for ioctl calls.
    """

    Tun = 0x0001
    """IFF_TUN."""

    Tap = 0x0002
    """IFF_TAP"""


class TapDevice:
    """Tun/Tap device object."""

    def __init__(self, mode: TapMode = TapMode.Tun, name: str = None, dev: str = '/dev/net/tun',
                 mtu: int = 1500, enable_packet_info: bool = False) -> None:
        """Initialize TUN/TAP device object.

        Args:
            mode: Select tun or tap device mode.
            name: The name of the new device. If not supplied, a default
                will be provided. An integer will be added to build the real device name.
            dev: The device node name the control channel is connected to.
            mtu: The MTU size, in bytes, to be applied to the new device.
            enable_packet_info: Whether or not to enable packet information header to be
                prepended to each
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

        self._enable_packet_info = enable_packet_info
        mode_value = self._mode.value
        if not self._enable_packet_info:
            mode_value |= IFF_NO_PI

        ifs = fcntl.ioctl(self._fd, TUNSETIFF,
                          struct.pack('16sH', self._name.encode(), mode_value))

        # Retrieve real interface name from control device.
        self._name = ifs[:16].strip(b'\x00').decode()

        self._mtu = mtu

        # Properly close device on exit.
        atexit.register(self.close)

    def __enter__(self) -> 'TapDevice':
        self.up()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    @property
    def name(self) -> str:
        """The device name."""
        return self._name

    @property
    def mode(self) -> TapMode:
        """The device mode (tap or tun)."""
        return self._mode

    @property
    def mtu(self) -> int:
        """The device MTU."""
        return self._mtu

    @property
    def is_packet_information_enabled(self) -> bool:
        """Whether packet information header is enabled for this device."""
        return self._enable_packet_info

    @property
    def fd(self) -> int:
        """The device file descriptor."""
        return self._fd

    def fileno(self) -> int:
        """The device file descriptor.

        This method is named specifically so that the object can be
        passed to select.select() calls.
        """
        return self._fd

    def read(self, num_bytes: int = None) -> bytes:
        """Read data from the device.

        Args:
            num_bytes: The number of bytes to read. If not specified, the MTU size is used,
                including the optional packet information header if enabled on a the device.
        """
        if num_bytes is None:
            num_bytes = self._mtu
            # If packet information is enabled, 4 extra bytes will be appended to a packet
            # that is potentially already the maximum MTU size, so ensure that by
            # default we can read one entire MTU-sized packet and this header.
            if self._enable_packet_info:
                num_bytes += PACKET_INFO_SIZE

        return os.read(self._fd, num_bytes)

    def write(self, data: bytes) -> None:
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

    def up(self) -> None:
        """Bring up device. This will effectively run "ifconfig up" on the device."""
        ret = os.system('ifconfig {} up'.format(self._name))

        if ret != 0:
            raise IfconfigError()

    def down(self) -> None:
        """Bring down device. This will effectively call "ifconfig down" on the device."""
        ret = os.system('ifconfig {} down'.format(self._name))

        if ret != 0:
            raise IfconfigError()

    def close(self) -> None:
        """Close the control channel.

        This will effectively drop all locks and remove the TUN/TAP device.

        You must manually take care that your code does not try to operate on the interface
        after closing the control channel.
        """
        try:
            os.close(self._fd)
        except OSError:
            pass


class IfconfigError(Exception):
    """Exception thrown if an ifconfig command returns with a non-zero exit status."""
