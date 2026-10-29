Python drivers for Galil motion controllers, used as analog voltage sources:

- `DMC30000` ([src/galil/dmc30000.py](src/galil/dmc30000.py)): DMC-30000 series (single-axis), e.g. the DMC-30014.
  Uses the controller's two analog outputs (AO1, AO2, +/-10V, 16-bit).
  Manuals: [datasheet](https://www.a2v.fr/galil/doc/cartes/dmc-3x01x/ds_3x01x.pdf),
  [user manual](https://www.a2v.fr/galil/doc/cartes/dmc-3x01x/man_3x01x.pdf)
- `DMC1846` ([src/galil/dmc1846.py](src/galil/dmc1846.py)): DMC-1846 (4-axis PCI card). It has no general purpose
  analog outputs, so it uses the +/-10V motor command lines of axes A-D (+/-9.9982V), with
  the servo gains zeroed and the voltage set by the offset (`OF`) command.
  Manual: DMC-1806 firmware command reference (covers the DMC-18x6 family)

Both share their gclib connection and command code through `GalilBase` ([src/galil/base.py](src/galil/base.py)).
The drivers know nothing about what is wired to the outputs; mapping outputs to a device
(e.g. the FSM's X/Y axes) is the job of the higher-level code.

for this to work you need to have gclib installed on your machine
you can do this on Windows or Linux but on macos you have to do some shenanigins (rosetta 2)

## Installing Galil gclib on Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install --upgrade --index-url https://www.galil.com/sw/pub/python gclib
```

check version

```python
import gclib
gclib.version()
# should show 2.5.0
```


## Userflow
Enter python shell with `python`

#### Assign IP Address to Galil (If Applicable)
```python
import gclib
gclib.ip_requests()
gclib.addresses()
# find address you want
# define variables mac_address and ip_addr or just input directly
# ip address should be same subnet as host computer
gclib.assign_ip(f'{mac_address}', f'{ip_addr}')
```
#### Connect Controller
```python
from galil import DMC30000
driver = DMC30000()
driver.connect(str(ip_addr)) # ip_addr must be ip address of the galil and be a string
```
#### Initialize and Set Analog Outputs
```python
driver.initialize()  # required before AO1 can be used as a general analog output
driver.set_analog_output(1, 0.5)  # AO1 to 0.5 V
driver.set_analog_output(2, -1.0)  # AO2 to -1.0 V
driver.get_analog_output(1)  # voltage currently output on AO1
```
#### DMC-1846 (PCI)
The DMC-1846 connects through Galil's PCI driver rather than ethernet, so there is no IP to
assign. Analog outputs are named by axis letter.
```python
from galil import DMC1846
driver = DMC1846(analog_axes=("A", "B"))  # only axes not driving a motor
driver.connect("GALILPCI1")  # Windows; on Linux use "/dev/galilpci0"
driver.initialize()  # zeroes the gains and maxes TL on the analog axes, servo on at 0V
driver.set_analog_output("A", 0.5)
driver.get_analog_output("A")  # motor command voltage currently output on axis A
```
#### Status and Errors
```python
driver.zero_outputs()  # set every analog output to 0V
driver.get_axis_status("A")  # AxisStatus flags, e.g. AxisStatus.MOTOR_OFF means the axis isn't driving its output
driver.get_stop_code("A")  # why the axis stopped, e.g. StopCode.STOPPED_BY_OFF_ON_ERROR
driver.last_error  # ErrorCode from the controller (TC) for the last failed command, or None
```
The codes are defined in [src/galil/codes.py](src/galil/codes.py).
#### Disconnect When Done
```python
driver.disconnect()
```
#### Useful Other Command
```python
driver._send_command("MG@AO[1]") # or 2
driver._read_reply()
```

## Useful Windows commmands
`.\.venv\Scripts\activate.ps1` to activate venv
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` to temporarily allow scripts to run
`Set-ExecutionPolicy RemoteSigned` to perminantly allow scripts to run (requires administrative privileges)
`ipconfig` to find current ip and subnet
