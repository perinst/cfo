Dòng tiền (cash flow) của một tổ chức là sự vận động tiền và tương đương tiền ra/vào trong một kỳ (ngày/tuần/tháng/quý). Mục tiêu là đảm bảo tổ chức luôn có thanh khoản để trả lương, nhà cung cấp, thuế… và phân bổ vốn hiệu quả cho tăng trưởng.

PHÂN LOẠI DÒNG TIỀN

Hoạt động kinh doanh (Operating – CFO): thu từ bán hàng, thu dịch vụ; chi lương, thuê, marketing, vận hành, thuế, lãi vay hoạt động…

Đầu tư (Investing – CFI): mua/bán TSCĐ, phần mềm, góp vốn, cho vay đầu tư, thu hồi đầu tư.

Tài trợ (Financing – CFF): nhận vốn chủ, phát hành nợ; chi cổ tức, mua lại cổ phiếu, trả nợ gốc/lãi.

THÀNH PHẦN DỮ LIỆU CỐT LÕI

Inflows: doanh thu đã thu (tiền/CK), hoàn thuế, thu lãi/cho vay, bán tài sản, giải ngân vốn.

Outflows: chi phí hoạt động (OPEX), CAPEX, trả lãi/gốc vay, thuế, cổ tức.

Vốn lưu động: phải thu (AR), phải trả (AP), tồn kho; lịch thanh toán/thu tiền, điều khoản tín dụng (DSO/DPO).

VẬN HÀNH QUY TRÌNH DÒNG TIỀN

Thu thập dữ liệu: đồng bộ sổ cái (GL), công nợ, đơn hàng, hợp đồng, bảng lương, kế hoạch mua sắm, lịch trả nợ.

Lập lịch dòng tiền: mapping từng khoản thu/chi vào mốc thời gian (cash calendar).

Theo dõi thực tế vs kế hoạch: đối soát bank feed mỗi ngày/tuần; reconcile sai lệch.

Ra quyết định: ưu tiên thanh toán, dời lịch, đẩy thu nợ, chiết khấu sớm, rút hạn mức tín dụng, đầu tư ngắn hạn phần thừa.

Kiểm soát: hạn mức phê duyệt, quy tắc cut-off, phân quyền, 4 mắt với khoản lớn.

DỰ BÁO (FORECASTING)

Phương pháp:
• Bottom-up theo dòng tiền: dựa hợp đồng/PO/Invoice, lịch trả nợ, kế hoạch lương/thuế/CAPEX.
• Theo mô hình thống kê/burn-rate: dùng chi tiêu lịch sử (30/60/90 ngày) để ước lượng chi tiêu tương lai.
• Kết hợp kịch bản: Base/Best/Worst theo tốc độ thu tiền, chậm thanh toán, doanh thu hụt.

Độ chi tiết: ngắn hạn (tuần/ngày) cho thanh khoản; trung hạn (3–6 tháng) cho kế hoạch; dài hạn (12–24 tháng) cho chiến lược.

Đầu vào quan trọng: tồn quỹ đầu kỳ, backlog doanh thu, tỷ lệ chuyển đổi pipeline, DSO/DPO, lịch CAPEX, hạn mức tín dụng.

CHỈ SỐ/KPI QUAN TRỌNG

Burn rate (tháng): tiền ròng chi ra mỗi tháng (đặc biệt với startup).

Runway: số tháng còn sống = tồn quỹ / burn rate.

Cash Conversion Cycle (CCC) = DSO + DIO – DPO (thấp hơn tốt hơn).

Operating Cash Flow margin; Current ratio; Quick ratio; Coverage ratio (EBITDA/Interest).

NGUYÊN TẮC & KIỂM SOÁT RỦI RO

Ưu tiên thanh khoản trước lợi nhuận kế toán; “cash is king”.

Bảo thủ với thu nhập chưa thu (AR); mô phỏng chậm thu 15–30–45 ngày.

Đa dạng hóa nguồn tiền: doanh thu, tín dụng ngắn hạn, tài trợ, tiền gửi kỳ hạn.

Cơ chế cảnh báo sớm: ngưỡng tồn quỹ tối thiểu, covenant nợ, biến động DSO/DPO bất thường.

LIÊN HỆ VỚI ĐOẠN CODE CỦA BẠN

monthly_burn_rate: lấy tổng chi 90 ngày/3 → cách “burn-rate” dựa lịch sử (đơn giản, nhanh).

pending_receivables: tổng invoice “pending” (AR chưa thu) → đại diện Inflows kỳ vọng.

net_position: receivables – (burn \* months) → ước lượng thặng dư/thâm hụt trong kỳ dự báo.

Hạn chế: chưa xét tồn quỹ đầu kỳ, lịch thời gian thu/chi theo ngày/tuần, rủi ro chậm thu/huỷ đơn, CAPEX/CFF, nghĩa vụ nợ, thuế/lương theo kỳ, kịch bản hóa.

GỢI Ý NÂNG CẤP THỰC TIỄN

Thêm cash_on_hand và undrawn_credit để tính runway chính xác.

Lịch hóa dòng tiền: phân rã theo tuần/ngày từ due_date của AR/AP thay vì gộp theo tháng.

Áp dụng kịch bản (p,50/p,90): giả định tỷ lệ thu đúng hạn vs trễ, mô phỏng Monte Carlo đơn giản.

Bao gồm CFI/CFF: CAPEX đã cam kết, lịch vay/trả nợ, cổ tức.

Theo dõi KPI: DSO/DPO/DIO, CCC, cảnh báo khi runway < X tháng.

Đối soát thực tế: log actuals và sai lệch (forecast vs actual) để cải thiện mô hình.
