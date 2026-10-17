# Board cứng TI-84 Plus CE → màn KD028QVFMA027 (rigid v2)

> **Trạng thái:** đã đặt JLC, chưa thử trên máy thật. v2 thay cho v1 (v1 ngược chân phía màn KD, không đưa lên đây). Board v2 dùng **dây FFC cùng chiều (A)**.

Thay cho bản flex (`../flex-v3-experimental`, đắt vì stiffener). Gồm 2 phần:

1. **Dây FFC mua trên Shopee:** nối đầu nối màn trên mainboard CE với board này.
2. **Board cứng 2 lớp 31.2 × 22.7 mm, dày 0.8 mm:** JLC hàn sẵn J1 (đầu nối dây FFC) và J2 (đầu nối cáp màn KD028).

Board chỉ có dây đồng, 1 điện trở và 2 tụ. Phần điện giống hệt bản flex: cùng sơ đồ chân, cùng chế độ SPI 3 dây + RGB.

## Các file

| File | Dùng để |
| --- | --- |
| `fab/JLC-1-gerber-upload-v2.zip` | Tải lên JLC ở bước đặt PCB |
| `fab/JLC-2-BOM-v2.csv` | Tải lên ở bước PCB Assembly, ô **BOM** |
| `fab/JLC-3-CPL-v2.csv` | Tải lên ở bước PCB Assembly, ô **CPL / Pick and place** |
| `print/ti84ce-kd028-rigid-in-1-1.pdf` | In ra (100%) để thử kích thước và xem cách cắm |
| `print/orientation-check.pdf` | Tờ kiểm tra chiều chân |
| `src/` | Script sinh file (`out_r.py`) và kiểm tra độc lập (`verify_r.py`) |

## 1. Mua dây FFC

- **39 chân (39P), bước 0.3 mm**, rộng khoảng 12 mm.
- **CÙNG CHIỀU** (Type A / same side / forward). **Không mua loại ngược chiều (B).**
- Đầu tiếp điểm dày 0.2 mm (loại chuẩn cho đầu nối 0.3 mm).
- Chiều dài: đo trong máy. Nên mua 2 độ dài (ví dụ 6 cm và 10 cm).

**Cách nhận biết:** đặt dây nằm phẳng trên bàn. Với loại cùng chiều, cả hai đầu đều thấy tiếp điểm vàng.

## 2. Kiểm tra trước khi đặt (để chắc chắn chạy ngay lần đầu)

Nên **mua màn và dây trước**, làm đủ 4 bước dưới đây rồi mới đặt board.

1. **Mainboard:** làm bước kiểm tra GND ở trang 2 của PDF. Ba chân GND liền nhau (35, 37, 39) phải nằm bên TRÁI.
2. **Màn KD028:** làm bước kiểm tra ở trang 3 của PDF.
   - Đặt màn ngửa, đuôi cáp chĩa vào J2.
   - Chân 1 phải ở bên TRÁI.
3. **Dây FFC:** cả hai đầu đều thấy tiếp điểm vàng (loại cùng chiều).
4. **Kích thước:** in trang 1 của PDF đúng 100%, cắt hình board ra và đặt thử vào chỗ định để trong máy.

Nếu bước 1 hoặc bước 2 cho kết quả ngược: **không đặt board**, báo lại. Sửa file chỉ mất vài phút.

## 3. Đặt JLCPCB

**PCB:**

| Mục | Chọn |
| --- | --- |
| Layers | 2 |
| Dimensions | 31.2 × 22.7 mm (JLC tự đọc) |
| PCB Qty | 5 |
| PCB Thickness | **0.8 mm** (mỏng nhất mà Economic PCBA nhận) |
| PCB Color | **Green** (khe mask giữa chân J2 chỉ 0.1 mm, màu đen/trắng không làm được) |
| Surface Finish | LeadFree HASL được. Nếu ENIG chỉ đắt hơn 1–2 USD thì chọn ENIG (pad phẳng hơn cho J1) |
| Via Covering | Tented |
| Remove Order Number | **Specify a location** (đã có chữ JLCJLCJLCJLC ở mặt dưới) |

**PCB Assembly:**

| Mục | Chọn |
| --- | --- |
| PCBA Type | Economic |
| Assembly Side | Top Side |
| PCBA Qty | 2 |
| Confirm Parts Placement | **Yes** (để JLC gửi ảnh vị trí linh kiện cho bạn duyệt) |

Ghi chú cho xưởng (copy vào ô Remark):

```
J1 = Hirose FH26W-39S-0.3SHW(60) (C92280): FPC opening (metal insertion guides, row of 20
leads on the 0.8 mm pads) must face the BOTTOM board edge (Y = 0); its black back-flip
actuator and the row of 19 leads face J2. J2 = Hirose FH12-50S-0.5SH(55) (C202116): FPC
opening / actuator must face the TOP board edge (Y = 22.7). Both are bottom-contact.
Please align J1 exactly to its pads.
J1 paste apertures in F_Paste are already reduced per the Hirose catalog:
0.23 x 0.65 / 0.23 x 0.55 mm.
```

**Kiểm tra ảnh xem trước của JLC:**
- **J1:** thanh khóa **màu đen quay lên phía J2**. Thân màu nâu, có 20 chân, quay về cạnh dưới, nơi dây FFC cắm vào (giống đầu nối trên mainboard CE: dây vào từ phía đối diện thanh đen). Góc xoay đúng trong CPL là **0**. Hàng dưới phải có 20 chân trên 20 pad, không pad nào trống.
- **J2:** nắp khóa quay về cạnh trên, chân hàn ở phía J1.
- Chân linh kiện phải nằm trùng pad. Nếu bị xoay hoặc lệch, chỉnh trong ảnh xem trước, hoặc trả lời email Confirm Parts Placement.

Giá ước tính khoảng 22 USD + ship. JLC sẽ hiện giá chính xác khi đặt.
- PCB 5 cái: ~2 USD.
- Economic setup: 8.18 USD.
- Stencil: 1.53 USD.
- Phí linh kiện Extended: 2 × 3.07 USD (J1, J2).
- Linh kiện: vài USD.

### Linh kiện

| Ký hiệu | Linh kiện | LCSC | Loại |
| --- | --- | --- | --- |
| J1 | Hirose FH26W-39S-0.3SHW(60), 39P 0.3 mm, tiếp điểm dưới (cùng loại với đầu nối trên mainboard CE) | C92280 | Extended |
| J2 | Hirose FH12-50S-0.5SH(55), 50P 0.5 mm, tiếp điểm dưới | C202116 | Extended |
| R1 | 100 kΩ 0402 (kéo chân TE của CE xuống GND) | C25741 | Basic |
| C1, C2 | 100 nF 16 V X7R 0402 (lọc IOVCC, VCC) | C1525 | Basic |

## 4. Lắp

1. **Tháo pin** trước mỗi lần cắm hoặc rút.
2. **Dây FFC:** cả hai đầu nối (trên mainboard và J1) đều là loại tiếp điểm dưới.
   - Ở mỗi đầu, mặt tiếp điểm vàng của dây **úp xuống board**, mặt nẹp hướng lên.
   - J1: lật thanh đen (phía J2) lên, đẩy dây vào từ cạnh dưới cho hết, rồi đóng thanh đen xuống.
   - Dây cùng chiều thì hai đầu như nhau.
   - Gập dây ở giữa không sao.
3. **Cáp màn KD028:**
   - Màn để ngửa, cáp gập ra sau như lúc giao hàng.
   - Đuôi cáp chĩa vào J2 từ cạnh trên, tiếp điểm úp xuống, chân 1 bên trái.
   - Đóng nắp khóa J2.
4. Lắp pin, bật máy.
   - Hình âm bản: cần chương trình bật đảo màu (INVON).
   - Đỏ và xanh dương đổi chỗ, hoặc hình bị lật: sửa bằng phần mềm (MADCTL).

## 5. Sơ đồ chân (đọc lại từ chính file Gerber)

| CE (GPM1421C0) | → | KD028QVFMA027 |
| --- | --- | --- |
| 1, 35, 37, 39 GND | → | 1, 42, 50 GND; 11 IM1 (=0); 16 WR (=0) |
| 2 TE | → | không nối, kéo xuống GND qua R1 |
| 3 RESET | → | 13 RESET |
| 4…21 DB17…DB0 | → | 40…23 DB17…DB0 |
| 22 SDO / 23 SDI | → | 41 SDO / 22 SDA |
| 24 WR/SCL / 25 CS | → | 15 RS(SPI-SCL) / 14 CS |
| 26 IOVCC | → | 6, 7 IOVCC; 10 IM2 (=1); 12 IM0 (=1); 17 RD (=1) |
| 27 VCC | → | 8, 9 VCI |
| 28 LED_A / 29…32 LED_K | → | 43 LEDA / 44…49 LEDK (gộp) |
| 33 VSYNC, 34 HSYNC, 36 DCLK, 38 ENABLE | → | 18, 19, 21, 20 |
| — | | 2–5 để trống |

## Đã kiểm tra

- Lỗ stencil của J1 thu nhỏ theo catalog Hirose: 0.23 × 0.65 mm (pad 0.8), 0.23 × 0.55 mm (pad 0.65), 0.3 × 0.7 mm (tai giữ). JLC không nhận stencil 0.10 mm cho đơn Economic nên dùng stencil mặc định. Với 0.12 mm, tỉ lệ diện tích lỗ là 0.68 (đạt, ≥ 0.66).

- DRC: khe hở đồng nhỏ nhất 0.150 mm trên cả 2 lớp (JLC cho phép 0.10). Đồng cách mép board ≥ 0.35 mm. Via 0.3/0.5 mm.
- Đọc lại file Gerber bằng một chương trình riêng:
  - Pad J1, J2, R, C khớp footprint KiCad chính thức (Hirose FH26-39S, FH12-50S) theo đúng tọa độ và góc xoay trong CPL.
  - Chiều chân suy ra lại từ loại dây (cùng chiều), bản vẽ cáp GPM1421C0 và bản vẽ cáp KD028.
  - Chạy thử với giả định dây ngược chiều thì chương trình báo FAIL, nghĩa là bài kiểm tra có bắt được lỗi lật chân.
  - 39 chân CE nối đúng chân KD như bảng trên, không chập, chân 2–5 của màn để trống.
