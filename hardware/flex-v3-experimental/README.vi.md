# Flex TI-84 Plus CE → màn KD028QVFMA027 (v3)

Miếng flex 2 lớp **thay cho cả dây FFC lẫn board cứng**: đầu hẹp cắm thẳng vào đầu nối màn trên mainboard CE, đầu rộng có J2 để cắm cáp màn KD028. Đây là **bản thử nghiệm, chưa từng đặt sản xuất** (quá đắt vì cần stiffener PI + FR4). Bản được đặt là `../rigid-v2`.

**v3 khác v2:** v2 (không đưa lên đây) bị ngược chiều chân phía màn KD. v3 giữ nguyên đường mạch của v2, chỉ chuyển **J2, R1, C1, C2 sang mặt dưới** và thêm một dải via ngay dưới J2 để đưa tín hiệu xuống mặt dưới. Lật J2 sang mặt kia làm đảo chiều chân, nên v3 đúng chiều.

## Các file

| File | Dùng để |
| --- | --- |
| `fab/JLC-FPC-1-gerber-v3.zip` | Tải lên JLCPCB → **Flex PCB** |
| `fab/JLC-FPC-2-BOM-v3.csv` | PCB Assembly, ô BOM |
| `fab/JLC-FPC-3-CPL-v3.csv` | PCB Assembly, ô CPL (cả 4 linh kiện ở **Bottom**) |
| `print/ti84ce-kd028-flex-v3-in-1-1.pdf` | In 100% để đặt thử vào máy |
| `images/preview-top.png`, `images/preview-bottom.png` | Hình hai mặt |

Board 36.2 × 75.25 mm, gồm đuôi hẹp 12 mm và cổ dài khoảng 40 mm.

## 1. Bắt buộc làm trước khi đặt

Bản flex **không có phương án đổi dây** như board cứng. Nếu đầu cắm phía CE ngược chiều, miếng flex sẽ hỏng luôn.

1. **Kiểm tra GND trên mainboard**, làm theo trang 2 của PDF board cứng. Ba chân GND liền nhau (35, 37, 39) phải nằm **bên TRÁI**. Nếu kết quả ngược lại thì **không đặt**.
2. **In file PDF đúng 100%**, cắt theo viền, đặt thử. Đuôi phải cắm tới được đầu nối trên mainboard, đầu rộng phải nằm được sau màn. Nếu cổ quá ngắn hoặc quá dài, báo lại để chỉnh.

## 2. Thông số đặt JLCPCB (Flex PCB)

| Mục | Chọn |
| --- | --- |
| Layers | 2 |
| Kích thước | 36.2 × 75.25 mm (JLC tự đọc) |
| Số lượng | 5 |
| FPC thickness | 0.11 mm |
| Surface finish | ENIG |
| Coverlay | Vàng (mặc định) |
| Stiffener | Tick cả **Polyimide** (chọn **0.15**) và **FR4** (chọn **0.4**). Vùng dán nằm trong file `pib_0.15.gbr` (PI mặt dưới) và `fr4t_0.4.gbr` (FR4 mặt trên), đặt tên theo quy ước của JLC |
| Gold Fingers | **Yes**, Gold Fingers Thickness = **0.2 mm**. JLC ưu tiên con số này khi chọn PI |
| Outline tolerance | ±0.05 mm nếu có tùy chọn (đuôi rộng 12.0 mm phải vừa đầu nối) |
| PCB Assembly | Có, **Bottom side**, 2 cái, Confirm Parts Placement = **Yes** |

**Remark:**
```
1) Gold fingers on the TOP side at the narrow end (y = 0..2.5 mm). They mate with a Hirose FH26
   0.3 mm pitch connector: total thickness at the fingers incl. PI stiffener = 0.20 +/- 0.03 mm
   (PI 0.15 mm chosen from your PI calculator; please adjust the PI so the total is 0.20 mm).
   Tail width 12.0 mm, please laser cut +/-0.05 mm.
2) PI stiffener on the BOTTOM side under the finger area (layer pib_0.15.gbr, 12 x 4.5 mm).
3) FR4 stiffener 0.4 mm on the TOP side of the wide end (layer fr4t_0.4.gbr), behind J2/R1/C1/C2.
4) SMT on the BOTTOM side only. J2 = Hirose FH12-50S-0.5SH(55) (C202116) on the BOTTOM:
   its FPC opening / actuator must face the wide board edge (max Y, away from the gold fingers);
   solder tails towards the gold fingers.
```

**Lúc duyệt ảnh xem trước:** J2 nằm ở mặt dưới. Nắp khóa phải quay về **cạnh rộng** của board, chân hàn quay về phía cổ flex. Kiểm tra kỹ ảnh trước khi bấm Confirm.

### Linh kiện (cả 4 linh kiện đều ở mặt dưới)

| Ký hiệu | Linh kiện | LCSC |
| --- | --- | --- |
| J2 | Hirose FH12-50S-0.5SH(55), 50 chân 0.5 mm, tiếp điểm dưới | C202116 |
| R1 | 100 kΩ 0402 | C25741 |
| C1, C2 | 100 nF 16 V X7R 0402 | C1525 |

## 3. Lắp

1. **Tháo pin.**
2. **Đuôi flex vào mainboard:** mặt có ngón vàng (chữ "MAT TIEP XUC") **úp xuống mainboard**. Mở lẫy đen, đẩy đuôi vào hết, đóng lẫy.
3. **Cáp màn vào J2:** quay mặt có J2 lên, sao cho khe J2 hướng ra xa người nhìn. Đuôi cáp màn chĩa vào khe, tiếp điểm vàng **úp xuống flex**. **Chân 1 nằm bên TRÁI**, giống bước kiểm tra màn của board cứng. Đóng khóa J2.
4. Đo chập C1 và C2 như hướng dẫn của board cứng. Không chập thì lắp pin, bật máy, chạy AKDFIX.

## 4. Đã kiểm tra

- **DRC:**
  - Khe đồng nhỏ nhất 0.10 mm.
  - Pad hở cách đồng khác ≥ 0.15 mm.
  - Đồng cách mép ≥ 0.30 mm. Riêng vùng ngón vàng ≥ 0.22 mm, trong giới hạn 0.2 mm của JLC.
  - Via 0.3/0.55 mm, loại chuẩn của JLC.
- **Đọc lại Gerber bằng chương trình riêng:**
  - Pad J2, R1, C1, C2 khớp footprint KiCad chính thức khi đặt ở mặt dưới.
  - Chiều chân suy ra lại từ bất biến hướng cáp: phía CE +1, phía KD −1.
  - Kết quả: 39 chân CE nối đúng chân KD như bảng của board cứng, không chập, chân 2–5 để trống. **PASS.**
  - Thử cố ý đảo chiều phía KD thì chương trình báo **FAIL**, nghĩa là bài kiểm tra bắt được lỗi ngược chân.
