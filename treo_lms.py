# Chạy bằng file chay.bat (tự cài thư viện, tự hỏi tài khoản lần đầu)
# Đổi tài khoản: python treo_lms.py --doi-tai-khoan
import base64
import ctypes
import getpass
import json
import os
import re
import shutil
import sys
import time
from ctypes import wintypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

THU_MUC = os.path.dirname(os.path.abspath(__file__))
FILE_TAI_KHOAN = os.path.join(THU_MUC, "taikhoan.json")
# Hồ sơ Chrome riêng để giữ phiên đăng nhập giữa các lần chạy
THU_MUC_PROFILE = os.path.join(THU_MUC, "chrome_profile")
URL_MAC_DINH = "https://lms.vnu.edu.vn/learn/lop-hoc/chi-tiet/24f6bb01-cd62-49a9-b325-d685f1740d37"

# ==========================================
# CẤU HÌNH TÙY CHỌN & BUFFER THỜI GIAN
# ==========================================
# Thêm buffer 20 giây cho mỗi bài học để server LMS ghi nhận trọn vẹn heartbeat
SAFETY_BUFFER_SECONDS = 20

# Thời gian mở lướt đối với tài liệu PDF / Slide / Đề cương không yêu cầu phút
DEFAULT_PDF_SECONDS = 90

# BẢNG TỪ ĐIỂN THỜI GIAN THEO TỪNG BÀI (Số phút tối thiểu quy định bởi LMS)
COURSE_DURATIONS = {
    # --- Mở đầu & Thông tin chung ---
    "NHỮNG THÔNG TIN ĐẶC BIỆT QUAN TRỌNG CẦN ĐỌC": 2,
    "KÊNH HỖ TRỢ KỸ THUẬT": 1,
    "Lời chào và hướng dẫn tham gia học tập": 2,
    "Video: Giới thiệu chung về học phần": 5,
    "Video: Giới thiệu về cấu trúc học phần": 5,
    "Video: Giới thiệu về đối tượng nghiên cứu": 5,
    "Phiếu khảo sát trước khi bắt đầu học phần": 2,

    # --- Bài 1 ---
    "1.1 Thông tin về bài học": 1,
    "Video 1: Khái niệm, đặc trưng, vai trò của nhà nước": 10,
    "Video 2: Nhà nước pháp quyền": 7,
    "Video 3: Nhà nước pháp quyền XHCN Việt Nam": 10,
    "Video 4: Xây dựng, hoàn thiện nhà nước pháp quyền XHCN Việt Nam": 5,
    "Nhà nước pháp quyền XHCNVN - Những giá trị, đặc trưng": 2,
    "Hoạt động 1: Thảo luận về nội dung bài học": 2,
    "Hoạt động 2: Nhật ký học tập Bài 1": 1,

    # --- Bài 2 ---
    "2.1 Giới thiệu bài học": 1,
    "Video 1: Khái niệm, đặc điểm bộ máy nhà nước": 5,
    "Video 2: Bộ máy nhà nước CHXNCN Việt Nam": 18,
    "Video 3. Các nguyên tắc tổ chức và hoạt động": 12,
    "Video 4: Chức năng của nhà nước": 7,
    "Video 5: Một số chức năng chủ yếu": 10,
    "Bài đọc 1: Giải pháp nâng cao hiệu lực": 2,
    "Bài đọc 2: Vai trò, chức năng của nhà nước": 2,
    "Hoạt động 1: Nhật ký học tập Nội dung 1": 1,
    "Video: Hình thức nhà nước Cộng hòa xã hội chủ nghĩa Việt Nam": 10,
    "Bài đọc bắt buộc (PDF): Hình thức nhà nước đương đại": 2,
    "Hoạt động 2: Nhật ký học tập Nội dung 2": 1,

    # --- Bài 3 ---
    "3.1 Giới thiệu bài học": 1,
    "Video 1: Khái niệm và các thuộc tính cơ bản của pháp luật": 10,
    "Video 2: Nguồn pháp luật, văn bản quy phạm pháp luật": 10,
    "Video 3: Chức năng của pháp luật": 6,
    "Bài đọc 1 (PDF): Giá trị của pháp luật": 2,
    "Bài đọc 2 (PDF): Bàn về án lệ": 2,
    "Bài đọc 3 (PDF): Mở rộng nguồn pháp luật": 2,
    "Hoạt động 1: Thảo luận tình huống": 2,
    "Hoạt động 2: Nhật ký học tập Bài 3": 1,

    # --- Bài 4 ---
    "4.1 Giới thiệu bài học": 1,
    "Video 1: Quy phạm pháp luật": 4,
    "Video 2: Quan hệ pháp luật": 7,
    "Video 3: Thực hiện pháp luật": 4,
    "Bài đọc 1 (PDF): Quan hệ pháp luật trong kỷ nguyên số": 2,
    "Hoạt động 1: Thảo luận theo các nội dung": 2,
    "Hoạt động 2: Nhật ký học tập bài 4": 1,

    # --- Bài 5 ---
    "5.1 Giới thiệu bài học": 1,
    "Video 1: Ý thức pháp luật": 10,
    "Video 2: Văn hoá pháp luật": 7,
    "Video 3: Khái niệm và dấu hiệu của vi phạm pháp luật": 10,
    "Video 4: Các yếu tố cấu thành vi phạm pháp luật": 5,
    "Video 5: Phân loại vi phạm pháp luật": 3,
    "Video 6: Trách nhiệm pháp lý": 5,
    "Bài đọc 1: Vai trò của ý thức pháp luật": 2,
    "Bài đọc 2: Ý thức pháp luật và xây dựng ý thức": 2,
    "Bài đọc 3: Xã hội học vi phạm pháp luật": 2,
    "Hoạt động 1: Thảo luận về nội dung bài học": 2,
    "Hoạt động 2: Nhật ký học tập Bài 5": 1,

    # --- Bài 6 ---
    "Video 1: Luật dân sự": 5,
    "Video 2: Luật tố tụng dân sự": 5,
    "Video 3: Khái niệm, đối tượng và nguồn Luật Hiến pháp": 5,
    "Video 4: Nội dung và chế định Luật Hiến pháp": 5,
    "Video 5: Khái niệm, phương pháp và nguồn Luật hành chính": 5,
    "Video 6: Tố tụng hành chính và Luật Tố tụng hành chính": 5,
    "Video 7: Luật Hình sự - Những vấn đề chung": 5,
    "Video 8: Luật Hình sự - Tội phạm, dấu hiệu tội phạm": 5,
    "Video 9: Luật Hình sự - Các yếu tố cấu thành tội phạm": 5,
    "Video 10: Luật Hình sự - Các giai đoạn phạm tội": 5,
    "Video 11: Luật Hình sự - Hình phạt": 5,
    "Video 12: Luật Tố tụng hình sự": 5,
    "Bài đọc 1: Pháp luật dân sự và tố tụng dân sự": 2,
    "Bài đọc 2: Bộ Luật hình sự năm 2015": 2,
    "Bài đọc 3: Vai trò của Bộ Luật dân sự năm 2015": 2,
}


def xac_dinh_thoi_gian_hoc(name, extra_text=""):
    """
    Chiến lược xác định thời gian 3 tầng:
    1. Kiểm tra bài loại trừ: Trắc nghiệm (cần làm bài tính điểm), Zoom (trực tiếp).
    2. Quét DOM động từ LMS (nếu hiển thị 'Phải học tối thiểu X phút').
    3. Tra cứu từ điển môn học COURSE_DURATIONS.
    4. Heuristic theo loại học liệu (Video, Bài đọc, PDF...).
    Trả về: (tong_so_giay, mo_ta_ly_do, loai_bai)
    loai_bai: 'NORMAL', 'QUIZ_SKIP', 'ZOOM_SKIP'
    """
    name_clean = " ".join(name.split())
    text_combined = f"{name_clean} {extra_text}".lower()

    # 1. Kiểm tra bài kiểm tra / Trắc nghiệm / Bài tính điểm
    # (không bắt chữ "kiểm tra" đơn lẻ: video "...trọng số kiểm tra, đánh giá" là bài thường)
    if re.search(r"trắc nghiệm kiểm tra|kiểm tra trắc nghiệm|tính điểm|phải đạt\s+\d+\s*\(?điểm\)?", text_combined):
        return 0, "Trắc nghiệm / Kiểm tra (Yêu cầu làm bài đạt điểm - Bỏ qua)", "QUIZ_SKIP"

    # 2. Kiểm tra Buổi học trực tiếp Zoom
    if re.search(r"\(zoom\)|buổi học trực tiếp", text_combined):
        return 0, "Buổi học trực tiếp Zoom (Bỏ qua)", "ZOOM_SKIP"

    # 3. Tầng 1: Đọc trực tiếp từ giao diện LMS nếu có text 'Phải học tối thiểu X (phút)'
    match_phut = re.search(r"tối thiểu\s+(\d+(?:\.\d+)?)\s*\(?phút\)?", text_combined)
    if match_phut:
        mins = float(match_phut.group(1))
        secs = int(mins * 60) + SAFETY_BUFFER_SECONDS
        return secs, f"Đọc từ LMS: {mins} phút (+{SAFETY_BUFFER_SECONDS}s buffer)", "NORMAL"

    # 4. Tầng 2: Tra từ điển COURSE_DURATIONS
    for key, mins in COURSE_DURATIONS.items():
        if key.lower() in name_clean.lower() or name_clean.lower() in key.lower():
            secs = int(mins * 60) + SAFETY_BUFFER_SECONDS
            return secs, f"Khớp từ điển: {mins} phút (+{SAFETY_BUFFER_SECONDS}s buffer)", "NORMAL"

    # 5. Tầng 3: Heuristic dự phòng thông minh
    name_lower = name_clean.lower()
    if "video" in name_lower:
        mins = 5
        return int(mins * 60) + SAFETY_BUFFER_SECONDS, f"Heuristic Video: {mins} phút (+{SAFETY_BUFFER_SECONDS}s buffer)", "NORMAL"
    elif any(k in name_lower for k in ["bài đọc", "thảo luận", "khảo sát"]):
        mins = 2
        return int(mins * 60) + SAFETY_BUFFER_SECONDS, f"Heuristic Bài đọc/Thảo luận: {mins} phút (+{SAFETY_BUFFER_SECONDS}s buffer)", "NORMAL"
    elif any(k in name_lower for k in ["thông tin", "nhật ký", "reflection"]):
        mins = 1
        return int(mins * 60) + SAFETY_BUFFER_SECONDS, f"Heuristic Thông tin/Nhật ký: {mins} phút (+{SAFETY_BUFFER_SECONDS}s buffer)", "NORMAL"
    elif any(k in name_lower for k in ["pdf", "tài liệu", "đề cương", "giáo trình", "học liệu", "hướng dẫn", "danh mục"]):
        return DEFAULT_PDF_SECONDS, f"Tài liệu/PDF đọc nhanh: {DEFAULT_PDF_SECONDS}s", "NORMAL"

    # Mặc định an toàn cho các mục chưa rõ
    return 90, "Mặc định: 1.5 phút (90s)", "NORMAL"


JS_DANH_SACH_BAI = """
return [...document.querySelectorAll('div.__lesson-status')].map(function (s) {
    var a = s.parentElement.querySelector('a');
    return [s.className, a ? a.textContent : ''];
});
"""

# Video bị dừng (Chrome chặn tự phát có tiếng) -> tắt tiếng rồi phát lại
JS_PHAT_VIDEO = """
var vids = document.querySelectorAll('video');
for (var i = 0; i < vids.length; i++) {
    if (vids[i].paused && !vids[i].ended) { vids[i].muted = true; vids[i].play().catch(function () {}); }
}
"""


def doc_danh_sach_bai(driver):
    """Trả về list (key, name, class) — key = tên + số thứ tự trùng tên,
    vì có bài trùng tên ở các chương khác nhau (vd 'Hoạt động 1: Thảo luận...')."""
    ket_qua = []
    dem_trung = {}
    for class_str, raw_text in driver.execute_script(JS_DANH_SACH_BAI):
        name = " ".join(raw_text.split()) if raw_text else "Bài học không có tên"
        dem_trung[name] = dem_trung.get(name, 0) + 1
        ket_qua.append((f"{name}#{dem_trung[name]}", name, class_str or ""))
    return ket_qua


def da_hoan_thanh(driver, key):
    try:
        for k, _, class_str in doc_danh_sach_bai(driver):
            if k == key:
                return "ico-img-status-3" in class_str
    except Exception:
        pass
    return False


def bai_bi_khoa(driver):
    """Nếu LMS báo 'Cần hoàn thành các nội dung sau để tiếp tục' -> trả về list bài chặn."""
    return driver.execute_script("""
        var h = [...document.querySelectorAll('h4')].find(function (x) {
            return x.offsetParent !== null && x.textContent.indexOf('Cần hoàn thành các nội dung sau') >= 0;
        });
        if (!h) return null;
        return [...h.parentElement.querySelectorAll('li')].map(function (li) { return li.textContent.trim(); });
    """)


def thoi_luong_video(driver):
    """Đợi tối đa 10s để video tải metadata, trả về số giây (0 nếu không có video)."""
    for _ in range(10):
        dur = driver.execute_script("""
            var v = document.querySelector('video');
            return v ? v.duration : null;
        """)
        if dur is None:
            return 0
        if dur and dur == dur and dur != float("inf"):  # bỏ NaN / Infinity
            return int(dur)
        time.sleep(1)
    return 0


def dem_nguoc(driver, tong_so_giay, ten_bai, key):
    """
    Đếm ngược thời gian trực quan theo phút:giây, giữ video luôn phát,
    và kết thúc sớm ngay khi LMS đánh dấu tích xanh cho bài.
    """
    start_time = time.time()
    last_interaction = start_time
    last_check = start_time

    while True:
        elapsed = time.time() - start_time
        remaining = int(tong_so_giay - elapsed)
        if remaining <= 0:
            break

        try:
            driver.execute_script(JS_PHAT_VIDEO)
        except Exception:
            pass

        # Tương tác cuộn nhẹ mỗi 35 giây để giữ phiên hoạt động (Heartbeat keepalive)
        if time.time() - last_interaction >= 35:
            try:
                driver.execute_script("window.scrollBy(0, 100); setTimeout(() => window.scrollBy(0, -100), 400);")
            except Exception:
                pass
            last_interaction = time.time()

        # Mỗi 10 giây xem LMS đã tích xanh chưa -> xong sớm thì chuyển bài luôn
        if time.time() - last_check >= 10:
            last_check = time.time()
            if da_hoan_thanh(driver, key):
                print(f"\n   ✅ LMS ĐÃ TÍCH XANH: {ten_bai[:50]}")
                return True

        m_rem = remaining // 60
        s_rem = remaining % 60
        m_tot = tong_so_giay // 60
        s_tot = tong_so_giay % 60
        print(f"   ⏳ [TREO MÁY] Còn {m_rem:02d}:{s_rem:02d} / {m_tot:02d}:{s_tot:02d} | {ten_bai[:45]}...", end="\r", flush=True)
        time.sleep(1)

    time.sleep(3)
    xong = da_hoan_thanh(driver, key)
    print(f"\n   {'✅ ĐÃ XONG' if xong else '⚠️ HẾT GIỜ NHƯNG LMS CHƯA TÍCH XANH'}: {ten_bai[:50]}")
    return xong


# ==========================================
# TÀI KHOẢN: lưu thẳng trong taikhoan.json, sửa tay file này để đổi tài khoản / mật khẩu
# ==========================================
def _giai_ma_dpapi_cu(b64):
    """Đọc mật khẩu dạng mã hoá DPAPI của bản cũ (để tự chuyển sang dạng thường)."""
    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    data = base64.b64decode(b64)
    buf = ctypes.create_string_buffer(data, len(data))
    blob_vao = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_ra = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_vao), None, None, None, None, 0, ctypes.byref(blob_ra)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(blob_ra.pbData, blob_ra.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree(blob_ra.pbData)


def luu_tai_khoan(tk):
    with open(FILE_TAI_KHOAN, "w", encoding="utf-8") as f:
        json.dump(tk, f, ensure_ascii=False, indent=2)


def nhap_tai_khoan():
    print("=" * 65)
    print("🔐 NHẬP TÀI KHOẢN VNU (chỉ hỏi lần đầu, lưu vào taikhoan.json)")
    print("=" * 65)
    username = ""
    while not username:
        username = input("👤 Tài khoản (mã SV / email VNU): ").strip()
    password = ""
    while not password:
        password = getpass.getpass("🔑 Mật khẩu (gõ sẽ không hiện ký tự): ")
    course_url = input("🔗 Link lớp học (Enter để dùng mặc định):\n   ").strip() or URL_MAC_DINH

    tk = {"username": username, "password": password, "course_url": course_url}
    luu_tai_khoan(tk)
    print("💾 Đã lưu tài khoản vào taikhoan.json.\n")
    return tk


def lay_tai_khoan(doi_tai_khoan=False):
    if doi_tai_khoan:
        # Xoá phiên Chrome cũ để không bị dính đăng nhập của tài khoản trước
        shutil.rmtree(THU_MUC_PROFILE, ignore_errors=True)
        return nhap_tai_khoan()
    if not os.path.exists(FILE_TAI_KHOAN):
        return nhap_tai_khoan()
    try:
        with open(FILE_TAI_KHOAN, encoding="utf-8") as f:
            cfg = json.load(f)
        password = cfg.get("password", "")
        if not password and cfg.get("password_dpapi"):
            password = _giai_ma_dpapi_cu(cfg["password_dpapi"])
        if not cfg.get("username") or not password:
            print("⚠️ taikhoan.json thiếu tài khoản hoặc mật khẩu, nhập lại nhé.")
            return nhap_tai_khoan()
        tk = {
            "username": cfg["username"],
            "password": password,
            "course_url": cfg.get("course_url") or URL_MAC_DINH,
        }
        if "password_dpapi" in cfg or "password" not in cfg:
            luu_tai_khoan(tk)  # chuyển file bản cũ sang dạng mật khẩu thường
        return tk
    except Exception as e:
        print(f"⚠️ Không đọc được taikhoan.json ({e}), nhập lại nhé.")
        return nhap_tai_khoan()


def _o_trang_dang_nhap(driver):
    url = driver.current_url
    return "idp.vnu.edu.vn" in url or "/signin" in url


def dang_nhap(driver, tk):
    driver.get(tk["course_url"])

    # Chờ xem LMS đưa về trang đăng nhập hay đã vào thẳng lớp học (phiên cũ còn)
    try:
        WebDriverWait(driver, 30).until(
            lambda d: _o_trang_dang_nhap(d) or d.find_elements(By.CSS_SELECTOR, "div.__lesson-status")
        )
    except TimeoutException:
        pass
    if not _o_trang_dang_nhap(driver):
        print("🔓 Phiên đăng nhập cũ vẫn còn, bỏ qua bước đăng nhập.")
        return

    print(f"🔐 Đang đăng nhập tài khoản: {tk['username']} ...")
    try:
        if "idp.vnu.edu.vn" not in driver.current_url:
            nut_vnu = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.login100-form-btn"))
            )
            driver.execute_script("arguments[0].click();", nut_vnu)

        o_user = WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.ID, "username")))
        o_user.clear()
        o_user.send_keys(tk["username"])
        o_pass = driver.find_element(By.ID, "password")
        o_pass.clear()
        o_pass.send_keys(tk["password"])
        driver.find_element(By.ID, "kc-login").click()

        WebDriverWait(driver, 30).until(lambda d: not _o_trang_dang_nhap(d))
        print("✅ Đăng nhập thành công!")
        return
    except TimeoutException:
        pass

    # Đăng nhập tự động không qua được: sai mật khẩu, cần OTP/QR, captcha...
    loi = driver.find_elements(By.CSS_SELECTOR, "#input-error, .pf-c-alert, .alert-error, .kc-feedback-text")
    loi_text = " ".join(e.text for e in loi if e.text.strip())
    if loi_text:
        print(f"❌ Trang đăng nhập báo: {loi_text}")
        print("   Nếu sai mật khẩu: chạy lại chay.bat và bấm D để đổi tài khoản.")
    print("👉 Hãy tự đăng nhập trong cửa sổ Chrome. Script sẽ chờ tối đa 5 phút...")
    try:
        WebDriverWait(driver, 300).until(lambda d: not _o_trang_dang_nhap(d))
        print("✅ Đăng nhập thành công!")
    except TimeoutException:
        print("❌ Hết thời gian chờ đăng nhập. Thoát.")
        driver.quit()
        sys.exit(1)


def cho_danh_sach_bai(driver, course_url):
    if "/learn/lop-hoc/" not in driver.current_url:
        driver.get(course_url)
    print("⏳ Đang chờ tải danh sách bài học...")
    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.__lesson-status"))
        )
        time.sleep(3)  # cho LMS render nốt các mục còn lại
    except TimeoutException:
        input("⚠️ Chưa thấy danh sách bài học. Mở đúng lớp trên Chrome rồi nhấn ENTER để bắt đầu...")


if __name__ == "__main__":
    tai_khoan = lay_tai_khoan("--doi-tai-khoan" in sys.argv)

    # ==========================================
    # KHỞI TẠO CHROME DRIVER
    # ==========================================
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-data-dir={THU_MUC_PROFILE}")
    options.add_argument("--hide-crash-restore-bubble")

    # chay.bat truyền đường dẫn Chrome tìm được qua biến CHROME
    if os.environ.get("CHROME") and os.path.exists(os.environ["CHROME"]):
        options.binary_location = os.environ["CHROME"]

    # Selenium Manager (có sẵn trong selenium >= 4.11) tự tải ChromeDriver khớp phiên bản Chrome
    driver = webdriver.Chrome(options=options)

    dang_nhap(driver, tai_khoan)
    cho_danh_sach_bai(driver, tai_khoan["course_url"])

    # Bộ nhớ phiên (theo key = tên + số thứ tự trùng tên)
    so_lan_thu = {}        # key -> số lần đã treo
    bo_qua = {}            # key -> (tên bài, lý do) : không xử lý nữa trong lần chạy này
    MAX_LAN_THU = 2

    while True:
        print("\n" + "=" * 65)
        print("📂 Mở rộng TOÀN BỘ các thư mục con lồng nhau...")

        # Bóc tách hết các thư mục bị đóng (hỗ trợ cả chevron-down và angle-down)
        while True:
            mui_ten_dong = driver.find_elements(
                By.CSS_SELECTOR, "i.fa-chevron-down, i.fa-angle-down"
            )
            if len(mui_ten_dong) == 0:
                break

            for icon in mui_ten_dong:
                try:
                    driver.execute_script("arguments[0].click();", icon)
                except:
                    try:
                        span_cha = icon.find_element(By.XPATH, "..")
                        driver.execute_script("arguments[0].click();", span_cha)
                    except:
                        pass
            time.sleep(1.5)

        print("🔄 ĐANG QUÉT TOÀN BỘ DANH SÁCH BÀI HỌC VÀ TRẠNG THÁI...")

        danh_sach = doc_danh_sach_bai(driver)
        so_hoan_thanh = 0
        danh_sach_chua_xong = []

        for vi_tri, (key, name, class_str) in enumerate(danh_sach):
            if "ico-img-status-3" in class_str:
                so_hoan_thanh += 1
            elif key not in bo_qua:
                danh_sach_chua_xong.append({"vi_tri": vi_tri, "key": key, "name": name})

        print(f"\n✅ ĐÃ XONG ({so_hoan_thanh} bài) | ⏭️ BỎ QUA ({len(bo_qua)} bài)")
        print(f"❌ CHƯA LÀM ({len(danh_sach_chua_xong)} bài)")
        print("=" * 65)

        if len(danh_sach_chua_xong) == 0:
            print("\n🎉 ĐÃ TREO XONG TẤT CẢ CÁC BÀI CÓ THỂ TREO!")
            if bo_qua:
                print("\n📝 CÁC BÀI BẠN CẦN TỰ LÀM / KIỂM TRA LẠI (làm xong rồi chạy lại chay.bat):")
                for ten, ly_do in bo_qua.values():
                    print(f"  ⭐ {ten}\n      ↳ {ly_do}")
            break

        # Luôn lấy bài đầu tiên trong danh sách CHƯA LÀM
        muc_tieu = danh_sach_chua_xong[0]
        ten_bai = muc_tieu["name"]
        key = muc_tieu["key"]

        # Phân tích thời gian và phân loại bài
        so_giay, ly_do, loai_bai = xac_dinh_thoi_gian_hoc(ten_bai)

        # Nếu là trắc nghiệm hoặc Zoom, bỏ qua ngay
        if loai_bai == "QUIZ_SKIP":
            print(f"\n⏭️ [BỎ QUA TRẮC NGHIỆM] {ten_bai}")
            bo_qua[key] = (ten_bai, "Trắc nghiệm / bài tính điểm - phải tự làm")
            continue

        if loai_bai == "ZOOM_SKIP":
            print(f"\n⏭️ [BỎ QUA ZOOM] {ten_bai}")
            bo_qua[key] = (ten_bai, "Buổi học Zoom - phải tự tham gia")
            continue

        if so_lan_thu.get(key, 0) >= MAX_LAN_THU:
            print(f"\n⏭️ [BỎ QUA] {ten_bai} (đã treo {MAX_LAN_THU} lần mà LMS chưa tích xanh)")
            bo_qua[key] = (ten_bai, f"Đã treo {MAX_LAN_THU} lần mà LMS chưa tích xanh "
                                    "(có thể phải tự viết thảo luận / nhật ký / nộp bài)")
            continue

        # Click vào bài học
        print(f"\n👉 ĐANG BẤM VÀO BÀI: {ten_bai}")
        try:
            driver.execute_script(
                "document.querySelectorAll('div.__lesson-status')[arguments[0]]"
                ".parentElement.querySelector('a').click();",
                muc_tieu["vi_tri"],
            )
        except Exception as e:
            print(f"   ⚠️ Lỗi khi click: {e}")
        time.sleep(4)

        # Bài bị khoá vì chưa xong bài trước -> không treo vô ích
        bai_chan = bai_bi_khoa(driver)
        if bai_chan is not None:
            ds_chan = "; ".join(bai_chan) or "(không rõ)"
            print(f"   🔒 BÀI BỊ KHOÁ, cần xong trước: {ds_chan}")
            bo_qua[key] = (ten_bai, f"Bị khoá, cần hoàn thành trước: {ds_chan}")
            continue

        # Có video -> treo ít nhất bằng độ dài video
        dur = thoi_luong_video(driver)
        if dur and dur + SAFETY_BUFFER_SECONDS > so_giay:
            so_giay = dur + SAFETY_BUFFER_SECONDS
            ly_do = f"Theo độ dài video: {dur // 60}:{dur % 60:02d} (+{SAFETY_BUFFER_SECONDS}s buffer)"
        print(f"   📊 Căn cứ thời gian: {ly_do}")

        so_lan_thu[key] = so_lan_thu.get(key, 0) + 1
        dem_nguoc(driver, so_giay, ten_bai, key)
        print("🔄 Chuyển sang bài tiếp theo...\n")
