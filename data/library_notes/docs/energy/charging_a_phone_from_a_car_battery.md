# Charging a phone from a car battery

How to keep phones and radios charged from a car battery when the power is out, without leaving the car unable to start.

This note was written for this library from documents already on the Energy shelf. Page numbers are the PDF page (the number your PDF viewer shows), with the printed page in parentheses.

En español: [Cargar el teléfono con la batería del carro](cargar_el_telefono_con_la_bateria_del_carro.html).

## The easy way: the car's own socket

Most cars have a 12-volt socket (the old cigarette-lighter socket) or USB ports. Plug a car USB adapter into the socket and charge the phone from it. Ready.gov's advice is to keep a phone charger in the car for exactly this ([Ready.gov, Get Tech Ready](../../mirrors/ready_gov/www.ready.gov/get-tech-ready.html), "In your car").

Many cars only power the socket with the key turned to "accessory" or the engine running. Accessory mode is enough for a phone. Turn the key back off when the phone is charged, so nothing else in the car keeps drawing on the battery.

## Do not flatten the starting battery

A car battery is a starter battery. It is built to give a big burst of current for a second or two to crank the engine, and it "cannot be deep-cycled" (Battery University, article BU-201). Battery University's table for starter batteries: drained all the way each time, one lasts 12 to 15 cycles; drained halfway each time, 100 to 120 cycles. Use a little at a time and recharge it.

Rough arithmetic, using the numbers on your own labels:

1. The car battery label gives its capacity in ampere-hours (Ah). A 50 Ah battery at 12 volts holds about 50 × 12 = 600 watt-hours (Wh). NEETS Module 1 explains ampere-hours and the 20-hour rating ([NEETS Module 1](neets/neets_module_01.pdf), PDF page 96 (2-18)).
2. Plan to use no more than half of that, about 300 Wh in this example.
3. A phone battery lists its size in Wh on the battery, the box or in the phone's settings. A phone that holds 15 Wh gets roughly 300 / 15 = 20 full charges out of that half, fewer after what the adapter wastes.

Charging one or two phones a day for a week is a small draw. Running a laptop, a fridge or lights from the same battery is not.

To put the charge back, start the engine and let it run for a while, or charge the battery with a solar panel through a charge controller ([Victron, Which solar charge controller: PWM or MPPT?](victron_pwm_vs_mppt_solar_charge_controllers_2020.pdf) explains the two kinds of controller).

## Never run the engine indoors

Run the engine only outside, never in a garage or shed, even with the door open. Engine exhaust has carbon monoxide, which you cannot see or smell. Headache, nausea and confusion in several people at once is the warning sign: [Hurt or sick, carbon monoxide](../../triage.html#co). Ready.gov gives the same rule for generators: outdoors only, at least 20 feet from windows ([Ready.gov, Power Outages](../../mirrors/ready_gov/www.ready.gov/power-outages.html)).

## If the battery is out of the car

You can buy a 12-volt socket with clamps or ring terminals and a fuse in the lead. Put it on the battery and use the same USB adapter. The rules from NEETS Module 1 (PDF page 96 (2-18) and PDF page 98 (2-20)):

- Never short the terminals. A wrench across the two posts can weld, burn you, or make the battery explode.
- No smoking, sparks or flames near a battery that is being charged. Charging gives off hydrogen, and a mix of hydrogen and air can explode.
- Wear gloves and eye protection. The liquid inside is acid. If it gets on skin or in an eye, flush with lots of fresh water for at least 15 minutes, holding the eyelids open.

Battery University article BU-403 adds: charge a lead-acid battery in a well-ventilated area.

## Where to read more

- [NEETS Module 1](neets/neets_module_01.pdf), chapter 2 "Batteries": how cells and batteries work, capacity, charging, safety.
- Battery University (batteryuniversity.com, online only; not in this library): BU-201 "How does the lead acid battery work", BU-403 "Charging lead acid", BU-903 "How to measure state-of-charge".
- [Victron, Which solar charge controller: PWM or MPPT?](victron_pwm_vs_mppt_solar_charge_controllers_2020.pdf), for charging a 12-volt battery from solar panels.
