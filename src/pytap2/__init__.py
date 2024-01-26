"""Module that wraps the Linux Tun/Tap device."""

import atexit
import enum
import fcntl
import os
import struct
import subprocess
from typing import Any, Optional

TUNSETIFF = 0x400454CA

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

    def __init__(
        self,
        mode: TapMode = TapMode.Tun,
        name: Optional[str] = None,
        dev: str = "/dev/net/tun",
        mtu: int = 1500,
        enable_packet_info: bool = False,
    ) -> None:
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
                self._name = "tun%d"
            elif self._mode is TapMode.Tap:
                self._name = "tap%d"
        else:
            self._name = name + "%d"

        # Open control device and request interface.
        self._fd = os.open(dev, os.O_RDWR)

        self._enable_packet_info = enable_packet_info
        mode_value = self._mode.value
        if not self._enable_packet_info:
            mode_value |= IFF_NO_PI

        ifs = fcntl.ioctl(
            self._fd,
            TUNSETIFF,
            struct.pack("16sH", self._name.encode(), mode_value),
        )

        # Retrieve real interface name from control device.
        self._name = ifs[:16].strip(b"\x00").decode()

        self._mtu = mtu

        # Properly close device on exit.
        atexit.register(self.close)

    def __enter__(self) -> "TapDevice":
        self.up()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, exc_tb: Any) -> None:
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

    def read(self, num_bytes: Optional[int] = None) -> bytes:
        """Read data from the device.

        Args:
            num_bytes: The number of bytes to read. If not specified, the MTU size is used,
                including the optional packet information header if enabled on the device.
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


    def ipconfig(self, **args: Any) -> None:
        """Issue iproute2 command on the device.

        Keyword Args:
            address: IP address of the device, can be in CIDR notation (see man ip-address).
            netmask: Network mask can use CIDR notation or 255.255.255.0.
            broadcast: Broadcast address, normally set automatically.
            mtu: Link MTU, this will also affect the read() method.
            hwclass: Hardware class, normally ether for ethernet.
            hwaddress: Hardware (MAC) address.
        """
        if 'address' in args:
            address_cmd = ['ip', 'address', 'add']
            address = args['address'].split('/', 1)
            address = address[0]
            if len(address) == 2:
                netmask = address[1]
            if 'netmask' in args:
                netmask = str(args['netmask'])
            if len(address) != 2 and 'netmask' not in args:
                netmask = '24'
            address_cmd.extend([f"{address}/{netmask}"])
            if 'broadcast' in args:
                address_cmd.extend(['broadcast', str(args['broadcast'])])
            address_cmd.extend(['dev', self._name])

            try:
                subprocess.run(address_cmd, check=True)  # ['ip', 'address', 'add', '10.116.0.5/255.255.255.0', 'broadcast', '10.116.0.7', 'dev', 'tun0']
            except subprocess.CalledProcessError as e:
                raise IpconfigError("Unable to set IP address, Error: ", e)
        else:
            raise IpconfigError('No address provided to ipconfig')

        link_cmds = []
        if 'mtu' in args:
            link_cmds.append(['ip', 'link', 'set', 'dev', self._name, 'mtu', str(args['mtu'])])
        if 'hwclass' in args:
            link_cmds.append(['ip', 'link', 'set', 'dev', self._name, 'type', str(args['hwclass'])])
        if 'hwaddress' in args:
            link_cmds.append(['ip', 'link', 'set', 'dev', self._name, 'address', str(args['hwaddress'])])

        for link_cmd in link_cmds:
            link_cmd_request = f'{link_cmd[5]} {link_cmd[6]}'  # mtu 1300
            try:
                subprocess.run(link_cmd, check=True)
            except subprocess.CalledProcessError as e:
                raise IpconfigError(f"Unable to set {link_cmd_request} Error: ", e)


    def ifconfig(self, **args: Any) -> None:
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
        ifconfig_cmd = "ifconfig {} ".format(self._name)

        try:
            ifconfig_cmd = "{} {} ".format(ifconfig_cmd, args["address"])
        except KeyError:
            pass

        try:
            ifconfig_cmd = "{} {} {} ".format(ifconfig_cmd, "netmask", args["netmask"])
        except KeyError:
            pass

        try:
            ifconfig_cmd = "{} {} {} ".format(ifconfig_cmd, "network", args["network"])
        except KeyError:
            pass

        try:
            ifconfig_cmd = "{} {} {} ".format(ifconfig_cmd, "broadcast", args["broadcast"])
        except KeyError:
            pass

        try:
            ifconfig_cmd = "{} {} {} ".format(ifconfig_cmd, "mtu", args["mtu"])
        except KeyError:
            pass

        try:
            ifconfig_cmd = "{} {} {} {} ".format(
                ifconfig_cmd, "hw", args["hwclass"], args["hwaddress"]
            )
        except KeyError:
            pass

        ret = os.system(ifconfig_cmd)

        if ret != 0:
            raise IfconfigError("ifconfig command failed.")

        # Save MTU if ifconfig was successful so buffer sizes can be adjusted.
        try:
            self._mtu = args["mtu"]
        except KeyError:
            pass

    def up(self) -> None:
        """Bring up device. using iproute2 or ifconfig"""
        try:
            subprocess.run(['ip', 'link', 'set', 'dev', 'tun0', 'up'], check=True)
        except subprocess.CalledProcessError:
            subprocess.run(['ifconfig', self._name, 'up'], check=True)
        except:
            raise IfconfigError(f'Unable to set interface {self._name} up Ensure iproute2 ( recommended ) or ifconfig is installed')

    def down(self) -> None:
        """Bring down device. using iproute2 or ifconfig"""
        try:
            subprocess.run(['ip', 'link', 'set', 'dev', self._name, 'down'], check=True)
        except subprocess.CalledProcessError:
            subprocess.run(['ifconfig', self._name, 'down'], check=True)
        except:
            raise IfconfigError(f'Unable to set interface {self._name} down. Ensure iproute2 ( recommended ) or ifconfig is installed')

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

class IpconfigError(Exception):
    """Exception thrown if an ipconfig command returns with a non-zero exit status."""
