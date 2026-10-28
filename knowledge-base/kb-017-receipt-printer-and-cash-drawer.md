---
id: KB-017
title: Receipt Printer and Cash Drawer Issues
category: pos-payments
audience_roles: [staff, agent, admin]
last_updated: 2026-04-14
owner: IT Service Desk
---

# Receipt Printer and Cash Drawer Issues

Each DinkPOS station has a thermal receipt printer and a cash drawer. The cash drawer is connected to the printer and opens when DinkPOS sends a print command for a cash sale.

## Printer is not printing

1. Check that the printer's power light is on and the cover is closed firmly.
2. Open the cover and check the paper. The shiny side of the thermal roll must face the print head; if the paper comes out blank, the roll is upside down.
3. Turn the printer off, wait 10 seconds, and turn it on again.
4. In DinkPOS, go to **Settings > Printers** and tap **Test print**.
5. If the test fails, check that the printer shows as **Connected**. If it shows **Not found**, restart the DinkPOS app.

## Receipts are faded or have gaps

- Replace the paper roll. Old or low-quality thermal paper fades.
- If a fresh roll still prints faded, raise a ticket; the print head may need cleaning or replacement.

## Paper jam

1. Turn off the printer.
2. Open the cover and gently pull out the jammed paper. Do not use scissors or metal objects near the print head.
3. Reload the roll and close the cover.

## Cash drawer will not open

1. Check that the drawer cable is plugged into the back of the printer.
2. Make sure the drawer is not locked with the key.
3. Try **DinkPOS > Open drawer** (requires Supervisor rights). If the drawer opens this way, the drawer is fine and the problem is with the print command; raise a ticket.
4. In an emergency, the branch manager can open the drawer with the manual key. Record the reason in the cash log.

## Customer wants a receipt reprinted or emailed

Go to **DinkPOS > Sales history**, find the sale by receipt number or time, and choose **Reprint** or **Email receipt**. Email receipts are sent only to the address the customer gives you at the counter; do not look up their address from other records.

## Spare parts

Spare paper rolls are kept at each front desk. Order more through the branch manager. Replacement printers and drawers are requested through a ticket; IT keeps one spare set at the Dasmariñas head office.
