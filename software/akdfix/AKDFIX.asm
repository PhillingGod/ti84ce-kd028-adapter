; AKDFIX - chinh man KD028QVFMA027 (ST7789V, IPS) tren TI-84 Plus CE
; Gui lenh SPI toi controller LCD (cach lam giong thu vien lcddrvce cua CE toolchain).
; Assemble: spasm -E -A kdfix.asm AKDFIX.8xp

; ---------------------------------------------------------------- equates (ti84pceg.inc)
_GetCSC               .equ 002014Ch
_PutS                 .equ 00207C0h
_NewLine              .equ 00207F0h
_ClrScrnFull          .equ 0020810h
_HomeUp               .equ 0020828h
_RunIndicOff          .equ 0020848h
_GetFieldSizeFromType .equ 000030Ch
_FindFirstCertField   .equ 0000310h
_FindField            .equ 0000314h
_Delay10ms            .equ 00003B4h
userMem               .equ 0D1A881h
curRow                .equ 0D00595h
curCol                .equ 0D00596h

mpSpiCtrl0            .equ 0F80000h
mpSpiCtrl1            .equ 0F80004h
mpSpiCtrl2            .equ 0F80008h
mpSpiStatus           .equ 0F8000Ch
mpSpiIntCtrl          .equ 0F80010h
mpSpiData             .equ 0F80018h

SPI_LCD_CTRL0         .equ 0Bh        ; MasterMono | ClkPhase | ClkPolarity
SPI_PY_CTRL0          .equ 1828h      ; SpiFrFmt | Flash | FsPolarity | MasterMono
SPI_PY_CTRL0B         .equ 2Bh        ; FsPolarity | MasterMono | ClkPhase | ClkPolarity
SPI_LCD_CTRL1         .equ 080001h    ; 9-bit frames, clock div 2
SPI_OS_CTRL1          .equ 02000Bh    ; TI-OS default
SPI_LCD_CTRL2         .equ 010Dh      ; TxEn | TxClr | RxClr | ChipEn
SPI_OS_CTRL2          .equ 010Ch      ; TxEn | TxClr | RxClr
SPI_CLR               .equ 0Ch        ; TxClr | RxClr
SPI_RESET             .equ 40h        ; ChipReset

skClear               .equ 0Fh
sk1                   .equ 22h
sk2                   .equ 1Ah
sk3                   .equ 12h
sk4                   .equ 23h
sk5                   .equ 1Bh
sk6                   .equ 13h
sk7                   .equ 24h

MADCTL_TI             .equ 08h        ; TI-OS default (BGR)

 .assume ADL=1
 .org userMem-2
 .db 0EFh, 07Bh

start:
	call	_RunIndicOff
	; rescue first: works even when nothing is visible
	ld	hl, tRescue
	call	lcdSendTable
	call	drawMenu
mainLoop:
	call	_GetCSC
	or	a
	jr	z, mainLoop
	cp	skClear
	jr	z, quit
	cp	sk1
	jr	nz, notK1
	ld	hl, tInvOn
	ld	de, sInvOn
	jr	apply
notK1:
	cp	sk2
	jr	nz, notK2
	ld	hl, tInvOff
	ld	de, sInvOff
	jr	apply
notK2:
	cp	sk3
	jr	nz, notK3
	ld	hl, tVendor
	ld	de, sVendor
	jr	apply
notK3:
	cp	sk4
	jr	nz, notK4
	ld	b, 08h                  ; BGR
	jr	toggleMad
notK4:
	cp	sk5
	jr	nz, notK5
	ld	b, 40h                  ; MX
	jr	toggleMad
notK5:
	cp	sk6
	jr	nz, notK6
	ld	b, 80h                  ; MY
	jr	toggleMad
notK6:
	cp	sk7
	jp	nz, mainLoop
	ld	a, MADCTL_TI
	ld	(madVal), a
	ld	hl, tDefault
	ld	de, sDefault
	jr	apply

toggleMad:
	ld	a, (madVal)
	xor	b
	ld	(madVal), a
	ld	(tMad+2), a
	ld	hl, tMad
	ld	de, sMad

apply:                                  ; hl = command table, de = status text
	push	de
	call	lcdSendTable
	pop	hl
	call	showStatus
	jp	mainLoop

quit:
	call	_ClrScrnFull
	call	_HomeUp
	ret

; ---------------------------------------------------------------- screen
drawMenu:
	call	_ClrScrnFull
	call	_HomeUp
	ld	hl, menuText
drawMenu_line:
	ld	a, (hl)
	or	a
	jr	z, drawMenu_end
	push	hl
	call	_PutS                   ; prints up to the 0, hl -> after it
	call	_NewLine
	pop	hl
drawMenu_skip:
	ld	a, (hl)
	inc	hl
	or	a
	jr	nz, drawMenu_skip
	jr	drawMenu_line
drawMenu_end:
	ld	hl, sStart
	; fall through

showStatus:                             ; hl = status text (<= 15 chars)
	push	hl
	ld	a, 9
	ld	(curRow), a
	xor	a
	ld	(curCol), a
	ld	hl, sBlank
	call	_PutS
	xor	a
	ld	(curCol), a
	pop	hl
	call	_PutS
	; " MAD=xx"
	ld	a, (madVal)
	ld	hl, sMadHex
	call	hexByte
	ld	hl, sMadTxt
	call	_PutS
	ret

hexByte:                                ; a -> two hex chars at (hl)
	push	af
	rrca
	rrca
	rrca
	rrca
	call	hexByte_nib
	pop	af
hexByte_nib:
	and	0Fh
	add	a, '0'
	cp	'9'+1
	jr	c, hexByte_ok
	add	a, 'A'-'9'-1
hexByte_ok:
	ld	(hl), a
	inc	hl
	ret

; ---------------------------------------------------------------- LCD over SPI
; table: { nParams, cmd, params... } ... 0FFh
lcdSendTable:
	push	hl
	call	lcdInit
	pop	hl
lcdSendTable_next:
	ld	a, (hl)
	cp	0FFh
	jr	z, lcdSendTable_done
	cp	0FEh                    ; 0FEh, n : wait n x 10 ms
	jr	nz, lcdSendTable_cmd
	inc	hl
	ld	b, (hl)
	inc	hl
	push	hl
	push	bc
	call	lcdWait
	pop	bc
	pop	hl
lcdSendTable_dly:
	push	hl
	push	bc
	call	_Delay10ms
	pop	bc
	pop	hl
	djnz	lcdSendTable_dly
	jr	lcdSendTable_next
lcdSendTable_cmd:
	ld	b, a
	inc	hl
	ld	a, (hl)
	inc	hl
	ld	c, 0                    ; D/C = 0 : command
	call	sendByte
	ld	a, b
	or	a
	jr	z, lcdSendTable_next
lcdSendTable_param:
	ld	a, (hl)
	inc	hl
	ld	c, 1                    ; D/C = 1 : parameter
	call	sendByte
	djnz	lcdSendTable_param
	jr	lcdSendTable_next
lcdSendTable_done:
	call	lcdWait
	; restore TI-OS SPI settings (lcd_Cleanup)
	ld	hl, SPI_OS_CTRL1
	ld	(mpSpiCtrl1), hl
	ld	hl, SPI_OS_CTRL2
	ld	(mpSpiCtrl2), hl
	ret

sendByte:                               ; a = byte, c = D/C bit; keeps hl, b
	push	hl
	ld	e, a
	ld	hl, mpSpiStatus+1
sendByte_wait:
	ld	a, (hl)
	cp	0F0h                    ; tx fifo nearly full -> wait
	jr	nc, sendByte_wait
	ld	hl, mpSpiData+1
	ld	(hl), c                 ; 9th bit (D/C)
	dec	hl
	ld	(hl), e                 ; low byte, pushes the frame
	pop	hl
	ret

lcdWait:
	ld	hl, mpSpiStatus+1
lcdWait_empty:
	ld	a, (hl)
	cp	10h
	jr	nc, lcdWait_empty
	dec	hl
lcdWait_busy:
	bit	2, (hl)
	jr	nz, lcdWait_busy
	ret

lcdInit:                                ; lcd_Init (lcddrvce)
	ld	a, (fullInit)
	or	a
	jr	nz, lcdInit_full
	ld	a, (mpSpiCtrl0)
	cp	SPI_LCD_CTRL0
	jr	z, lcdInit_fast
lcdInit_full:
	xor	a
	ld	(fullInit), a
	; Python model check (certificate field 0430h inside 0330h)
	ld	de, 0330h
	call	_FindFirstCertField
	jr	nz, lcdInit_notPython
	call	_GetFieldSizeFromType
	ld	de, 0430h
	call	_FindField
	jr	nz, lcdInit_notPython
	call	000654h
	ld	de, SPI_PY_CTRL0
lcdInit_pyLoop:
	ld	(mpSpiCtrl0), de
	ld	hl, SPI_CLR
	ld	(mpSpiCtrl2), hl
	ld	hl, SPI_RESET
	ld	(mpSpiCtrl2), hl
	push	de
	call	_Delay10ms
	pop	de
	bit	0, e
	ld	e, SPI_PY_CTRL0B
	jr	z, lcdInit_pyLoop
	ld	hl, 21h
	ld	(mpSpiIntCtrl), hl
lcdInit_notPython:
	ld	a, SPI_LCD_CTRL0
	ld	(mpSpiCtrl0), a
lcdInit_fast:
	ld	hl, SPI_LCD_CTRL1
	ld	(mpSpiCtrl1), hl
	ld	hl, SPI_LCD_CTRL2
	ld	(mpSpiCtrl2), hl
	ret

; ---------------------------------------------------------------- data
fullInit:	.db 1
madVal:		.db MADCTL_TI

tInvOn:		.db 0, 21h
		.db 0FFh
tInvOff:	.db 0, 20h
		.db 0FFh
tMad:		.db 1, 36h, MADCTL_TI
		.db 0FFh
; KD028QVFMA027 vendor values (3SPI+18bit RGB init code), interface/orientation untouched
; rescue on start: sleep out, wait 120 ms, display on, then vendor values + INVON
tRescue:	.db 0, 11h                      ; SLPOUT
		.db 0FEh, 12                    ; 120 ms
		.db 0, 29h                      ; DISPON
tVendor:	.db 1, 0B7h, 70h                ; gate voltages
		.db 1, 0BBh, 21h                ; VCOM
		.db 1, 0C2h, 01h
		.db 1, 0C3h, 0Bh                ; VRH
		.db 1, 0C4h, 27h                ; VDV
		.db 2, 0D0h, 0A4h, 0A1h         ; power control
		.db 14, 0E0h, 0D0h,06h,0Bh,09h,08h,30h,30h,5Bh,4Bh,18h,14h,14h,2Ch,32h
		.db 14, 0E1h, 0D0h,05h,0Ah,0Ah,07h,28h,32h,2Ch,49h,18h,13h,13h,2Ch,33h
		.db 0, 21h                      ; INVON
		.db 0FFh
; TI-OS defaults: INVOFF, MADCTL 08, TI gamma (lcd_SetDefaultGamma)
tDefault:	.db 0, 20h
		.db 1, 36h, MADCTL_TI
		.db 14, 0E0h, 0D0h,00h,00h,10h,0Fh,1Ah,2Dh,54h,3Fh,3Bh,18h,17h,13h,17h
		.db 14, 0E1h, 0D0h,00h,00h,10h,0Fh,09h,2Bh,43h,40h,3Bh,18h,17h,13h,17h
		.db 0FFh

menuText:
		.db "AKDFIX v2 (KD028)", 0
		.db "1 Dao mau (INVON)", 0
		.db "2 Bo dao mau", 0
		.db "3 Thong so hang+INVON", 0
		.db "4 Doi do<>xanh duong", 0
		.db "5 Lat kieu 1 (MX)", 0
		.db "6 Lat kieu 2 (MY)", 0
		.db "7 Ve mac dinh TI", 0
		.db "CLEAR: thoat", 0
		.db 0
sBlank:		.db "                         ", 0
sStart:		.db "Da: goi day du", 0
sInvOn:		.db "Da: dao mau", 0
sInvOff:	.db "Da: bo dao", 0
sVendor:	.db "Da: thong so hang", 0
sMad:		.db "Da: doi MADCTL", 0
sDefault:	.db "Da: mac dinh TI", 0
sMadTxt:	.db " MAD="
sMadHex:	.db "00", 0
