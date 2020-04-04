``pytap2`` - Object oriented interface to Linux Tun/Tap devices
===============================================================

.. image:: https://travis-ci.com/johnthagen/pytap2.svg?branch=master
    :target: https://travis-ci.com/johnthagen/pytap2

.. image:: https://codeclimate.com/github/johnthagen/pytap2/badges/gpa.svg
   :target: https://codeclimate.com/github/johnthagen/pytap2

.. image:: https://codeclimate.com/github/johnthagen/pytap2/badges/issue_count.svg
   :target: https://codeclimate.com/github/johnthagen/pytap2

.. image:: https://codecov.io/github/johnthagen/pytap2/coverage.svg
    :target: https://codecov.io/github/johnthagen/pytap2

.. image:: https://img.shields.io/pypi/v/pytap2.svg
    :target: https://pypi.python.org/pypi/pytap2

.. image:: https://img.shields.io/pypi/status/pytap2.svg
    :target: https://pypi.python.org/pypi/pytap2

.. image:: https://img.shields.io/pypi/pyversions/pytap2.svg
    :target: https://pypi.python.org/pypi/pytap2/

Fork of `PyTap <https://pypi.python.org/pypi/PyTap/>`_ that supports Python 3.

Installation
------------

You can install, upgrade, and uninstall ``pytap2`` with these commands:

.. code:: shell-session

    $ pip install pytap2
    $ pip install --upgrade pytap2
    $ pip uninstall pytap2

Usage
-----

Using as a context manager automatically brings up the device and closes it at the
end of the ``with`` block.

.. code:: python

    from pytap2 import TapDevice

    with TapDevice() as device:
        device.ifconfig(mtu=1300)
        device.write(b'0000')

Or manually call ``up()`` and ``close()``.

.. code:: python

    from pytap2 import TapDevice

    device = TapDevice()
    device.up()
    device.ifconfig(mtu=1300)
    device.write(b'0000')
    device.close()

The ``fileno()`` method is defined, so that the device object can be passed directly
to `select() <https://docs.python.org/library/select.html#select.select>`_.

Releases
--------

2.0.0 - 2020-03-29
^^^^^^^^^^^^^^^^^^

- Drop Python 2.7.

1.6.0 - 2019-12-15
^^^^^^^^^^^^^^^^^^

- Drop Python 3.4 and support Python 3.8.
- Include license file.

1.5.0 - 2018-07-09
^^^^^^^^^^^^^^^^^^

Support Python 3.7.

1.4.0 - 2017-10-24
^^^^^^^^^^^^^^^^^^

Allow disabling packet information header (``IFF_NO_PI``) and default ``read()`` to read entire
MTU worth of data plus the packet information header if present.

1.3.0 - 2017-07-31
^^^^^^^^^^^^^^^^^^

Add ``fileno()`` method to support ``select()`` calls.

1.2.0 - 2017-06-19
^^^^^^^^^^^^^^^^^^

Context manager support added.

1.1.0 - 2017-06-17
^^^^^^^^^^^^^^^^^^

Allow ``read()`` to be called with a specific number of bytes to read.


1.0.0 - 2017-06-16
^^^^^^^^^^^^^^^^^^

Initial release that supports Python 2 and 3.
