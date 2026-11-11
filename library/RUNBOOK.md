# Library operator runbook

Print this. Tape a copy inside the box lid. Walk one other person in the
household through Part 1 and Part 2 while you are both standing at the box.
If only one person knows how to run it, the library is only as reliable as
that one person.

Part 1 and Part 2 need no computer skills. Part 3 and Part 4 are for whoever
maintains the box; they assume you can type a command into a terminal when
the runbook tells you exactly what to type.

Version of this build: see the bottom of the library's [front page](index.html). It shows
two numbers, the library version (the date the content was last sealed, for
example 2026.09.28) and the image version (the software on the boot disk,
for example 1.0.5). Both live in files on the box, so what you see there is
what is actually running.

---

## Part 1: Daily use (anyone)

**Turn it on**

1. Plug the Pi (the small black box) into a power bank with the USB-C
   cable. Plug the router (the white GL.iNet box) into the other power bank.
   Both have a light that comes on.
2. Wait 2 minutes.
3. On any phone, tablet, or laptop, join the Wi-Fi network called
   **LIBRARY**. It has no password.
4. Open a browser and type **http://library.lan** in the address bar, with
   the `http://`: without it, Safari and some other browsers search the web
   for the words instead. The library opens. Other web addresses do not
   work on LIBRARY. Many phones also show a "sign in to network" pop-up on their own;
   that is the same library. The pop-up never says you are signed in, so
   close it the right way to stay on LIBRARY: on an iPhone tap Cancel, then
   **Use Without Internet** ("Use Other Network" drops the Wi-Fi). On
   Android, if the phone asks whether to keep a Wi-Fi with no internet,
   answer yes. Then use the phone's normal browser. To stop the pop-up on an
   iPhone: Settings, Wi-Fi, the (i) next to LIBRARY, Auto-Login off.
5. If the name does not work, type **10.10.10.10** instead. That always
   works when the box is on.

**Find things**

- Someone is hurt or sick: tap [SYMPTOM TRIAGE](triage.html) on the front page.
- Everything else is on the front page: food, water, power, maps, repair,
  and so on.
- [Wikipedia](ref:zim:wikipedia) and the other encyclopedias (they need the server running): front page, Encyclopedias section.
  They open at [library.lan:8080](http://library.lan:8080/). The [Search page](search.html) also searches them; it needs the server too.
- Maps that give directions: on an Android phone, install Organic Maps or
  OsmAnd from [tools/android/](tools/android/) (one-time; the README there
  has the steps), then copy the map files over from the [maps page](map.html).
  There is no offline map app here for iPhones; on an iPhone use the
  [browser map](map.html) while on the LIBRARY Wi-Fi. The browser map cannot
  show where you are and has no place search: find a town or street by
  panning and zooming until its name shows. For a dot that follows you, you
  need Organic Maps or OsmAnd on an Android phone.
- AI assistants: an app that speaks the MCP protocol can connect to
  http://library.lan/mcp and search the whole library. An AI is a helper,
  not a source. Medicine doses come from the printed drug guide (Davis's,
  see Part 5) or the dosing card made from it, never from an AI.
- The [Ask page](chat.html) (front page, "Ask") takes plain questions and shows the
  emergency cards and a list of matching pages from the library, each a link. It quotes
  no text: open a page to read it. It works with no laptop: the pages come in search
  order. An AI program on a laptop on the LIBRARY Wi-Fi only puts the most useful pages
  first; it writes nothing you read. The steps are in
  [tools/llamafile/README.md](tools/llamafile/README.md).
  Never eat a plant or mushroom because an AI said it was fine.

**Turn it off**

Wait 30 seconds after the last person is done, then unplug the Pi. The worst
case is that the box checks its disk on the next start, which adds a minute.

**Put it away**

When the library is not in use, all of the electronics go back in the Faraday
box (a closed metal box, which shields them from an electromagnetic pulse):
the Pi with its drive, the router, the backup SSD, the recovery cards and
both power banks. Close the lid fully. The power banks need charging at
least every 6 months (Part 4, item 6).

**How long the batteries last**

Each Anker PowerCore III Elite bank (25,600 mAh, about 92 Wh) runs the Pi
alone for roughly 15 hours, or the Pi and the router together for roughly
7 hours. Two banks, one per device, give about 15 hours of service (each
bank runs its own device for about 15 hours), not a full day. Recharge them
from the Anker Nano 47 W charger when there is power, or from any USB-C
source (car, solar) when there is not. These runtimes are estimates from the
power draw (Pi about 5 W, router about 5 W); measure once and write the real
number here: ________ hours.

---

## Part 2: When it does not work

Work from the top. Stop when the library loads.

The "sign in to network" pop-up may stop appearing on newer phones over the
years. Phone makers change how they detect Wi-Fi sign-in pages, and this box
cannot follow them. Typing http://library.lan (or 10.10.10.10) in the browser
always works.

**1. No LIBRARY Wi-Fi network shows up**

The router is off. Check its power bank is charged (press the button on the
bank; the lights show the level) and the USB-C cable is fully seated at both
ends. Try the other bank. Wait 90 seconds after power comes back.

If the router has power (its light is on) and there is still no LIBRARY
network after 3 minutes, the router has failed. This build has no spare
router. Two ways forward:

- Use the library with a cable: plug a laptop into the Pi's Ethernet port
  (a USB-to-Ethernet adapter if the laptop has no port). On the laptop, set
  the wired connection to address 10.10.10.20, netmask 255.255.255.0. Open
  http://10.10.10.10. Names like library.lan will not work this way; the
  number does.
- Replace the router. Any GL.iNet travel router works. Set it up from the
  checklist in Part 3.

**2. LIBRARY Wi-Fi joins, but no page loads**

Type http://library.lan in the address bar (with the `http://`) and press Go. If that fails, type
10.10.10.10. If that also fails, restart the Pi: unplug its USB-C cable,
count to 10, plug it back in, wait 3 minutes, try again.

Still nothing? The Pi is not starting properly. Your content is safe; it
lives on two other copies. Go to step 3.

**3. The Pi does not start (no page after 3 minutes)**

The Pi keeps its software in three places: the NVMe drive (a stick of memory
screwed to the board underneath the Pi), a microSD card in the slot on the
Pi's underside, and a second microSD card kept with the backup SSD. The Pi
tries the NVMe first, then the card in the slot. Both cards hold a copy of
the same software; the library content lives on the NVMe and on the backup
SSD (the Samsung T5, a palm-sized silver drive).

a. Plug the backup SSD into one of the Pi's blue USB ports, then restart the
   Pi (unplug, count to 10, plug in). Wait 3 minutes. If the NVMe was the
   problem, the Pi starts from the card in the slot, finds the library on the
   SSD, and serves it from there. Everything works except the Kolibri kids'
   lessons. Leave the SSD plugged in and carry on. [PHOTO: SSD in blue port]

b. Still nothing? The NVMe is failing in a way that stops the Pi before it
   can fall back to the card. Unplug power. Open the case, unclip the short
   flat ribbon cable that joins the NVMe board to the Pi (lift the black
   latch, slide the ribbon out). Plug power back in with the SSD attached.
   Wait 3 minutes. [PHOTO: ribbon latch]

c. Still nothing? The card in the slot has also failed. With the ribbon
   still off, push the card in to release it, and put in the second card
   (kept with the backup SSD). Plug power in. Wait 3 minutes.
   [PHOTO: card slot]

d. Still nothing? The Pi itself is dead. Go to step 4.

**4. The Pi is dead**

Any Raspberry Pi 5 becomes the library: put either microSD card in it, plug
the backup SSD into a blue USB port, plug in power, wait 3 minutes. The
router does not care which Pi is behind it. A new Pi starts from the card on
its own. Before moving the NVMe over to it, set its boot order once (Part 3,
"Setting the boot order"); otherwise it keeps starting from the card.

Without a Pi, a laptop running Linux can read the backup SSD directly (open
the library folder on it and double-click index.html; the PDFs, plant photos,
and this runbook work as plain files; the encyclopedias need the Kiwix
program from `tools/kiwix_desktop/` on the SSD, one file, no install). Mac and Windows laptops cannot read
this SSD without extra software. That was a deliberate choice: the SSD is
formatted so the Pi can serve from it (step 3a), and the two formats do not
mix. A replacement Pi 5 costs less than the software to teach a Mac to read
the drive.

**5. Nothing electronic works**

The paper shelf: printed [Where There Is No Doctor](ref:wtnd) and
[Where There Is No Dentist](ref:dentist), the [USDA canning guide](ref:usda_canning), the triage tree, the water card, the dosing
card, and this runbook. Its location is written on the card inside the lid.

---

## Part 3: The build

Everything in this section describes the box as it was actually built, not
as it was planned for the reference build. The inventory is the reference
build's parts list dated 2026-09-28. Prices are what the parts cost on that
date, for reference when replacing one; memory and storage prices were
unusually high then.

**Inventory**

| Part | Qty | Reference price | Notes and modern replacement |
|---|---|---|---|
| Raspberry Pi 5, 16 GB (PiShop.us budget kit K2B-1346-16GB) | 1 | $339.95 | Kit includes a HighPi Pro case (unused) and a USB-C power supply. 16 GB gives Kolibri room. |
| Pimoroni NVMe Base (PiShop.us 830-1) | 1 | $16.00 | Mounts the NVMe under the Pi on a ribbon cable. Pimoroni lists the 970 EVO Plus as "maybe"; it runs hot and has reported dropouts under heavy load. It has been fine serving the library. |
| Samsung 970 EVO Plus 2 TB NVMe (M.2 2280) | 1 | $499.99 | Boot disk plus library. The $499.99 listing was an overpriced marketplace seller; the same drive was about $182 from others, or $310 recertified. Any 2 TB M.2 2280 NVMe on Pimoroni's compatibility list works. |
| Raspberry Pi Active Cooler (PiShop.us 374-1) | 1 | $6.00 | Heatsink and blower on the processor. |
| Samsung PRO Endurance 32 GB microSD | 2 | $123.98 for two | Recovery cards: one in the slot, one with the SSD. $61.99 each was overpriced; SanDisk Extreme PRO 32 GB is $37.99. Any 32 GB or larger card works. As built: 32 GB in the slot, 64 GB on the shelf. |
| Pimoroni NVMe Base Case (PiShop.us 1460-2) | 1 | $17.00 | Replaces the kit's HighPi case. |
| Noctua NF-A6x15 FLX 60 mm fan | 1 | $17 | Case fan, 15 mm thick. |
| OwlTree USB 5 V to 12 V fan controller (2-pack) | 1 | $10 | Powers the fan from USB and sets its speed. Second unit is the spare. |
| GL.iNet Beryl AX (GL-MT3000) router | 1 | about $100 | Makes the LIBRARY Wi-Fi. No spare in this build; any GL.iNet travel router can replace it (checklist below). |
| Samsung T5 2 TB portable SSD | 1 | $299.99 | Backup of the whole library plus a copy of the boot image. Discontinued; replacement is the SanDisk Extreme Portable 2 TB (USB-C, $299.99 sale, $423.99 list). |
| Anker PowerCore III Elite power bank (25,600 mAh) | 2 | | One for the Pi, one for the router. Any USB-C PD bank of 20,000 mAh or more works. |
| Anker Nano 47 W two-port GaN USB-C charger | 1 | $25.99 | Recharges both banks. |

Total of the listed prices: about $1,460, plus the two power banks.

**Power.** The Pi 5 asks for 5 V at 5 A over USB-C; the power banks supply
5 V at 3 A. That is enough for a Pi with no screen and no keyboard, as long
as `usb_max_current_enable=1` is in `/boot/firmware/config.txt`. The boot
image sets it. If you ever build a new image by hand, put it back.

**Software.** The Pi runs Raspberry Pi OS Lite (64-bit) from a boot image
built from the files in `image/` in the build project. That folder is not on the box or the SSD; the image file itself is (see "Where the copies are" below). Seven services start on boot:
nginx (serves the library pages and answers phones' "sign in to network"
checks), kiwix (the kiwix-serve program, the encyclopedias, port 8080), Kolibri 0.19.5 (kids'
lessons, port 8081), the embedding server (lantern-embed, port 8091, search by
meaning), the MCP server (lantern-mcp, port 8090, reachable at /mcp; lets AI
apps search and read the library, with the Part 5 safety rules built into the
server), the voice server (lantern-voice, port 8092, reachable at /stt; turns
speech from the Ask page's microphone button into text; browsers offer the
microphone only over a secure connection, so phones on the plain http
library get no button and type instead), and the disc mounter
(lantern-discs; mounts the CD3WD disc images read-only so /discs/ browses
them like folders). The service names to type are `nginx`, `kiwix`, `kolibri`,
`lantern-embed`, `lantern-mcp`, `lantern-voice` and `lantern-discs`; for example
`systemctl status kiwix`. `systemctl --failed` names any service that failed. One more,
`lantern-firstboot`, runs at every start but only does work on the first one (below).
Kolibri is set up once with a facility and an admin account; learners need
no login, its usage reporting is off, and its data folder and the MCP
database are not served by the web server. The Kolibri admin login is in the
Network table below. On its first start each
box makes its own ssh keys, machine ID and disk ID, caps its system partition at
20 GB, and puts the rest of the disk in a partition labelled LANTERN mounted
at /data. The library lives at /data/library.

Each image carries its version in `/etc/lantern-release` (also served at
`library.lan/image-release.txt`, on the box only, not in the library folder): the image number, the git commit of
the files it was built from, the build date, the hardware it was tested on,
and the oldest library version it can serve. The library carries its own
version in [VERSION.json](VERSION.json) at the top of the library folder. The front page
footer shows both.

**Network.** The router runs OpenWrt (GL.iNet's firmware). Settings:

| Setting | Value |
|---|---|
| Wi-Fi name | LIBRARY, no password (the sign-in pop-up only appears on open networks) |
| Router address | 10.10.10.1, netmask 255.255.255.0 |
| Pi address | 10.10.10.10 (fixed lease for the Pi's MAC address, and also set on the Pi itself) |
| Names | library.lan (router DNS), library.local (from the Pi), or 10.10.10.10 |
| Wildcard DNS | every name anyone types goes to 10.10.10.10, with a second entry for library.lan |
| Router admin page | http://10.10.10.1 |
| Pi ssh | `lantern@10.10.10.10` takes this box's own key only and refuses a password (the key pair is `.keys/boxes/NAME/lantern_ed25519` on the build computer, made by `deploy/new_box.sh NAME identity`; keep a copy with the printed record card; where: ________). The console password for `lantern` (keyboard and screen on the Pi; `sudo` asks for it) is on the record card, printed by the same step. The firewall lets port 22 in only from 10.10.10.0/24, but the router puts the Wi-Fi on that same network, so phones and laptops on LIBRARY can reach port 22 too; the key keeps them out. |
| Kolibri admin | User `lantern`; the password was made on the box when Kolibri was set up. It is written on the printed record card and in `/etc/lantern/kolibri-admin.pw` (read it with `sudo cat`). Learners need no login. |

Setting up a replacement router, in the router's admin page:

1. Router mode. Wi-Fi name LIBRARY, security off.
2. LAN address 10.10.10.1, netmask 255.255.255.0. (GL.iNet's default is
   192.168.8.1; change it or nothing lines up.)
3. Fixed address for the Pi: Clients, find the Pi, pin it to 10.10.10.10.
   Or in LuCI: Network, DHCP and DNS, Static Leases.
4. Wildcard DNS: LuCI, Network, DHCP and DNS, Addresses, add two lines,
   `/#/10.10.10.10` and `/library.lan/10.10.10.10`. The router keeps every
   name ending in .lan for its own devices, so the first line does not
   cover library.lan. Without the second line the pop-up says "server
   cannot be found" and the phone drops the Wi-Fi. Over ssh instead:
   `uci add_list dhcp.@dnsmasq[0].address='/#/10.10.10.10'; uci add_list dhcp.@dnsmasq[0].address='/library.lan/10.10.10.10'; uci commit dhcp; /etc/init.d/dnsmasq restart`
5. Test with a real phone: join LIBRARY, see the library in the pop-up,
   tap Cancel and Use Without Internet, then open http://library.lan in the
   phone's normal browser too.

The router does DNS only. The Pi's nginx answers the phone makers' check
URLs (captive.apple.com, connectivitycheck.gstatic.com,
msftconnecttest.com and the other addresses phones use for that check) and
redirects to the library. It
serves the library only for the names library.lan, library.local, and
10.10.10.10, and redirects every other name to library.lan.

Do not restore a router settings backup from one model onto a different
model. It can brick the router.

**How the Pi starts.** The Pi's bootloader is set once to try the NVMe,
then the microSD slot, then USB (`BOOT_ORDER=0xf416`, `PCIE_PROBE=1`).
`sudo rpi-eeprom-config` prints the current setting; both lines must be in
it. The 32 GB card in the slot holds boot image 1.0.5. The NVMe runs the
same 1.0.5 software, but it was upgraded to it in place rather than written
from the image file; `/etc/lantern-release` says so. The card
cannot be removed while the NVMe ribbon is attached, and it does not need to
be: if the NVMe is not detected, the Pi starts from the card on its own. A
card-started Pi has no library on its own disk, so it looks for the backup
SSD (the partition labelled LANTERN_BAK) and serves the library from there,
read-only. That is Part 2 step 3a. Kolibri needs to write to its data and
does not run in this mode.

**Setting the boot order** (a new Pi 5, or one whose bootloader was reset).
Such a Pi does not have the two lines above: it starts from the card when
one is in the slot, and it may not find the NVMe at all. Start it from a
recovery card, log in over ssh as lantern, and type:

```
sudo rpi-eeprom-config --edit
```

An editor opens with the current settings. Make these two lines read
exactly like this (change them if they are there, add them at the end if
not):

```
BOOT_ORDER=0xf416
PCIE_PROBE=1
```

BOOT_ORDER is read from right to left: 6 is the NVMe, 1 the microSD card,
4 USB, and f means start over. So: try the NVMe, then the card, then USB.
PCIE_PROBE=1 tells the Pi to look for the NVMe adapter, which does not
announce itself. Save and close the editor (Ctrl-O, Enter, Ctrl-X). The new
setting takes effect at the next restart. After that restart, check it:
`sudo rpi-eeprom-config` prints the current settings, and both lines must be
there.

**Where the copies are.**

| What | Where | How current |
|---|---|---|
| Boot image (software) | NVMe; 32 GB card in the slot; 64 GB card with the SSD; the file `image/lantern-boot-<version>+g<commit>.img` on the SSD (for example `lantern-boot-1.0.5+g58aee6632.img`; `ls /mnt/bak/image/` shows the current name, with a `.sha256` beside it) | Both cards and the SSD file are image 1.0.5 and are rewritten together at each image release. The NVMe was upgraded in place to 1.0.5 (see "How the Pi starts"). |
| Library (content) | NVMe at /data/library; SSD at /library | SSD synced quarterly and after any content change |

**Rewriting the recovery cards** (after any image release). From the running
Pi, with the SSD plugged in and the shelf card in a USB card reader:

```
sudo mkdir -p /mnt/bak
mountpoint -q /mnt/bak || sudo mount -L LANTERN_BAK /mnt/bak
IMG=/mnt/bak/image/lantern-boot-1.0.5+g58aee6632.img   # use the current file name: ls /mnt/bak/image/
sudo /opt/lantern/lantern-write-card.sh $IMG        # the card in the USB reader
sudo /opt/lantern/lantern-write-card.sh $IMG slot   # the card in the Pi's slot
sudo umount /mnt/bak
```

The script is `/opt/lantern/lantern-write-card.sh`. It finds the one card in
a USB reader by itself. It refuses to write to the disk the Pi is running
from, to any disk with a partition labelled LANTERN or LANTERN_BAK (the
backup SSD), to a disk that is neither USB nor the card slot, and to a card
smaller than the image. It asks you to type `yes`, writes, reads the card
back, gives the card its own disk ID (so the Pi cannot mistake the card for
the NVMe at start), and prints OK. `slot` means the card in the Pi's own
slot.

A card that has started a Pi even once (for example in the yearly fallback
test in Part 4) made its own LANTERN partition on that first start, and the
script refuses it ("holds a LANTERN/LANTERN_BAK partition"). Write such a
card once by hand, then run the script on it as usual. First find the card,
because `dd` to the wrong device erases it:

```
lsblk -o NAME,SIZE,TRAN,MODEL,LABEL
findmnt -no SOURCE /
```

The reader's card is `/dev/sdX` (about 59.5G, usb). The slot card is
`/dev/mmcblk0` (about 29.7G). Never the NVMe (`nvme0n1`, 1.8T), never the
SSD (1.8T Samsung Portable SSD T5, label LANTERN_BAK), and never the disk
the second line names (the one the Pi is running from). Then, with the SSD
mounted and `IMG` set as in the first three lines above:

```
D=/dev/sdX     # the card from lsblk; /dev/mmcblk0 for the slot card
sudo umount ${D}?* 2>/dev/null
sudo dd if=$IMG of=$D bs=4M conv=fsync status=progress
sudo partprobe $D && sudo udevadm settle
sudo /opt/lantern/lantern-write-card.sh $IMG $D
```

The `dd` line removes the old LANTERN partition. The last line checks the
card again, writes it a second time (a few minutes), reads it back, and gives
it its own disk ID: a new random number, with the card's `cmdline.txt` and
`/etc/fstab` changed to match. Do not skip it. A card that keeps the image's
disk ID shares it with the other card, and the Pi can then start its system
from the wrong disk.

**Rebuilding from nothing** (new NVMe, or new Pi with an NVMe):

1. Start the Pi from a recovery card with the SSD plugged in (Part 2, step
   3). Log in over ssh as lantern. On a new Pi, or one whose bootloader was
   reset, set the boot order now ("Setting the boot order" above); the
   restart in step 3 puts it into effect.
2. Write the image to the NVMe. The file is `/mnt/bak/image/lantern-boot-<version>+g<commit>.img`;
   `ls /mnt/bak/image/` shows the current name (if it shows nothing, run the
   first two lines of step 4 first). Then
   `sudo dd if=/mnt/bak/image/lantern-boot-1.0.5+g58aee6632.img of=/dev/nvme0n1 bs=4M conv=fsync status=progress`
3. Unplug the SSD, restart. The Pi starts from the NVMe, makes its
   partitions and identity (about 2 minutes), and shows a "copy the
   library" page.
4. Plug the SSD back in and copy the library over (1 to 2 hours over USB 3
   for 1.3 TB):
   ```
   sudo mkdir -p /mnt/bak
   mountpoint -q /mnt/bak || sudo mount -L LANTERN_BAK /mnt/bak
   sudo rsync -aH --info=progress2 /mnt/bak/library/ /data/library/
   cd /data && sha256sum -c --quiet library/MANIFEST.sha256 && echo all files OK
   sudo umount /mnt/bak
   ```
   The sha256sum check reads every file and takes 1.5 to 2 hours on the Pi
   (it hashes about 220 MB a second). It prints nothing but the final line
   when all is well, so a quiet screen does not mean it has stopped.
5. Restart once more. Check from a phone: join LIBRARY, open http://library.lan,
   run a search, open a Wikipedia article.

### Checking a copy against the seal

Every sealed library carries two files at its top: VERSION.json (the seal)
and MANIFEST.sha256 (one line per file). `verify.sh` compares them.

- On the box: `sh /data/library/verify.sh`
- From a copy (the SSD, a laptop): `sh verify.sh` inside the library folder,
  or `sh verify.sh /path/to/library`

It prints the library version, the seal date, the file count, and two
hashes. MATCH means the manifest on this copy is the one that was sealed:
nothing in the file list has been swapped or edited. The manifest hash it
prints must equal the one in the footer of the library's front page. That
takes a few seconds and checks the manifest only.

`sh verify.sh --full` also hashes every file against the manifest, the same
1.5-to-2-hour check as `sha256sum -c` above, and lists any file that is damaged
or missing. Copy a listed file back from the SSD. The script exits 0 only
when everything passed, so it can gate a backup.

---

## Part 4: Maintenance (every 3 months, while there is grid power, about 2 hours plus waiting)

The easy way: open [MAINTENANCE_PROMPT.md](MAINTENANCE_PROMPT.md) (on Lantern, type
http://library.lan/MAINTENANCE_PROMPT.md), paste it into an AI coding assistant on a laptop that is
on the LIBRARY Wi-Fi. The agent runs the checks, tells you when to plug
things in, and writes a summary for the paper log.

By hand:

1. Service check from a phone on LIBRARY: front page loads, a search
   returns results, triage opens, a Wikipedia article opens.
2. Content refresh (only while online): check download.kiwix.org for newer
   encyclopedia files. Once a year, refresh the map extract too. Follow
   [REFRESH.md](REFRESH.md) (on Lantern, type http://library.lan/REFRESH.md).
3. System updates (only while online): `sudo apt update && sudo apt upgrade`.
4. Full file check, overnight, on the Pi. It runs in the background, so it
   keeps going when the ssh session closes or the laptop sleeps:
   ```
   sudo -v
   D=$(date +%F); echo "$D"
   sudo nohup sh -c "cd /data && sha256sum -c --quiet library/MANIFEST.sha256 > /home/lantern/verify_$D.log 2>&1; echo \"finished, exit \$?\" > /home/lantern/verify_$D.done" > /dev/null 2>&1 &
   ```
   Write down the date the second line prints. The next morning, in a new
   ssh session:
   ```
   D=2026-10-27    # the date the second line printed
   cat /home/lantern/verify_$D.done
   cat /home/lantern/verify_$D.log
   ```
   If there is no `.done` file yet, the check is still running
   (`pgrep -a sha256sum` shows it); look again later. If there is no `.done`
   file and nothing is running, the check was stopped: start it again.
   An empty log means every file matched, but only once the `.done` file
   says "finished, exit 0". Any line in the log names a file that is damaged or
   missing; copy that file back from the SSD.
5. Backup to the SSD, on the Pi, with the SSD in a blue USB port:
   ```
   sudo mkdir -p /mnt/bak
   mountpoint -q /mnt/bak || sudo mount -L LANTERN_BAK /mnt/bak
   mountpoint -q /mnt/bak && echo SSD mounted || echo "STOP: SSD not mounted"
   mountpoint -q /mnt/bak && sudo rsync -aH --delete --info=progress2 /data/library/ /mnt/bak/library/
   mountpoint -q /mnt/bak && (cd /mnt/bak && sudo sha256sum -c --quiet library/MANIFEST.sha256) && echo backup OK
   sudo umount /mnt/bak
   ```
   If the third line prints "STOP: SSD not mounted", do not go on: the copy
   would fill the Pi's own small system disk. Check the SSD's cable and port,
   unplug and replug it, and start again from the first line. The copy and check
   lines only run when the SSD is mounted.
   Unplug the SSD and put it back with the spare card.
6. Batteries: store the two power banks at 50 to 60% (about half the
   lights). Top them up to that level every time the backup SSD is plugged
   in for this check, and never leave them longer than 6 months without a
   charge. They live in the Faraday box with the rest of the electronics. Replace a bank that clearly holds
   less than it used to; it will fail on the day you need it.
7. If the image version changed since last time, rewrite both recovery
   cards (Part 3).
8. Write the date and anything unusual in the paper notebook kept with the
   box.
9. Put all of the electronics back in the Faraday box (Part 1, "Put it
   away") and close the lid.

Once a year, in addition: start the Pi from the recovery card with the SSD
attached (Part 2, steps 3a and 3b, on purpose) and confirm the library loads
from the SSD. Put the ribbon back. This is the only way to know the fallback
works before you need it.

Before a known outage: do items 2, 4 and 5 now, charge both banks to full,
print the network table from Part 3 and tape it inside the lid.

---

## Part 4b: If the person who maintains this is gone

Have one other person do a full Part 4 cycle with you watching, before they
have to do it alone. The plugging and unplugging is what needs to be seen
once; the commands are written out above.

The minimum that keeps the library alive, for someone who has never done
it: every 3 months, run Part 4 items 5, 6 and 8. Once a year, item 4.

Things to leave alone unless you understand them:

- Do not replace an encyclopedia file unless the download finished and its
  size matches the download page.
- Do not run `apt upgrade` with no internet. It does nothing useful and
  wastes an hour.
- Do not edit `MANIFEST.sha256` by hand. Build tools regenerate it.
- Do not restore a router backup onto a different router model.

---

## Part 5: Content safety rules (do not relax these)

- **Doses:** the printed drug guide only: Davis's Drug Guide for Nurses on the
  desk, the Lippincott Pocket Drug Guide for Nurses in the go-bag, and the
  Harriet Lane Handbook for children. Not
  Tarascon, which stopped in 2020. Never Wikipedia, never HISTORICAL docs,
  never AI models in `tools/`. The library's own pages, summaries and search
  never state a dose; the medical books on the shelf do.
- **`docs/HISTORICAL/` and Survivor Library:** background/technique history
  only. Never for food preservation recipes or drug guidance. See
  [docs/HISTORICAL/README-WARNING.txt](docs/HISTORICAL/README-WARNING.txt)
  (on Lantern: front page, Historical medical shelf, the warning at the top).
- **Canning:** 2015 USDA guide / NCHFP only (botulism is unforgiving).
- **Foraging:** no positive multi-feature ID = don't eat. Mushrooms are
  expert-gated. Photos on the [Plants, mushrooms & the coast](plants.html) page (on
  Lantern: front page; the files are in `docs/plant_id/`) include deadly
  lookalikes on purpose.
- **Practice while it's easy:** work through the [Skills checklist](_app/skills.html) (on Lantern: front
  page sidebar, Skills checklist; the file is `SKILLS_CHECKLIST.md`), one
  drilled rep per core skill beats a terabyte of unread PDFs.
