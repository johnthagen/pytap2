``pytap2`` - Object oriented interface to Linux Tun/Tap devices
===============================================================

.. image:: https://travis-ci.org/johnthagen/pytap2.svg
    :target: https://travis-ci.org/johnthagen/pytap2

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

Fork of `PyTap <https://pypi.python.org/pypi/PyTap/>`_ that supports Python 2 & 3.

Installation
------------

You can install, upgrade, and uninstall ``pytap2`` with these commands:

.. code:: shell-session

    $ pip install pytap2
    $ pip install --upgrade pytap2
    $ pip uninstall pytap2

Usage
-----

.. code:: python

    from pytap2 import TapDevice

    device = TapDevice()
    device.up()
    device.ifconfig(mtu=1300)
    device.write(b'0000')
    device.close()

Releases
--------

1.1.0 - 2017-06-17
^^^^^^^^^^^^^^^^^^

Allow ``read()`` to be called with a specific number of bytes to read.


1.0.0 - 2017-06-16
^^^^^^^^^^^^^^^^^^

Initial release that supports Python 2 and 3.
