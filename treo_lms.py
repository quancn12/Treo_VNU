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
# Thêm buffer 20 giây cho mỗi bài học để server LMS ghi nhận trọn vẹn
SAFETY_BUFFER_SECONDS = 20

# Bài KHÔNG bắt buộc (không có thời gian tối thiểu): chỉ cần mở qua là LMS tích xanh
GIAY_BAI_KHONG_BAT_BUOC = 15

# Dự phòng khi không đọc được API của LMS
DEFAULT_PDF_SECONDS = 90

API_LMS = "https://lms.vnu.edu.vn/dhqg.lms.api/api/v1"

# Gọi API LMS bằng chính token đăng nhập đang lưu trong trình duyệt
JS_GOI_API = """
var cb = arguments[arguments.length - 1];
fetch(arguments[0], {headers: {'Authorization': 'Bearer ' + localStorage.getItem('access_token')}})
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(cb).catch(function () { cb(null); });
"""


def doc_thong_tin_lop(driver, course_url):
    """
    Lấy từ API LMS thông tin TỪNG MỤC của lớp (dùng được cho mọi môn):
      mincore    : số phút tối thiểu (với bài kiểm tra thì là điểm cần đạt)
      isRequired : bài bắt buộc hay không
      type.title : Video / Tệp tài liệu / Văn bản / Bài kiểm tra / Bài tập
    Trả về dict: key "tên#thứ tự trùng tên" -> node, hoặc {} nếu lỗi.
    """
    m = re.search(r"chi-tiet/([0-9a-fA-F-]{36})", course_url)
    if not m:
        return {}
    try:
        driver.set_script_timeout(60)
        res = driver.execute_async_script(JS_GOI_API, f"{API_LMS}/LmsClassContent/frGetByClassId/{m.group(1)}")
    except Exception:
        return {}
    if not res or not isinstance(res.get("data"), list):
        return {}

    # Duyệt cây theo đúng thứ tự hiển thị (orderNum) để khớp thứ tự trên danh sách bài
    ket_qua = {}
    dem_trung = {}

    def duyet(ds):
        for node in sorted(ds, key=lambda n: n.get("orderNum") or 0):
            if not node.get("isFolder"):
                name = " ".join((node.get("title") or "").split())
                dem_trung[name] = dem_trung.get(name, 0) + 1
                ket_qua[f"{name}#{dem_trung[name]}"] = node
            duyet(node.get("childrens") or [])

    duyet(res["data"])
    return ket_qua


def xac_dinh_thoi_gian_hoc(name, info=None):
    """
    Trả về: (tong_so_giay, mo_ta_ly_do, loai_bai)
    loai_bai: 'NORMAL', 'QUIZ_SKIP'
    Ưu tiên dữ liệu từ API LMS (info); không có thì đoán theo tên bài.
    """
    name_clean = " ".join(name.split())

    if info:
        loai = ((info.get("type") or {}).get("title") or "").lower()
        if "kiểm tra" in loai or "bài tập" in loai:
            return 0, f"{(info.get('type') or {}).get('title')} - phải tự làm", "QUIZ_SKIP"
        mincore = info.get("mincore")
        if info.get("isRequired") and mincore:
            secs = int(float(mincore) * 60) + SAFETY_BUFFER_SECONDS
            return secs, f"LMS yêu cầu tối thiểu {mincore} phút (+{SAFETY_BUFFER_SECONDS}s buffer)", "NORMAL"
        return GIAY_BAI_KHONG_BAT_BUOC, f"Bài không bắt buộc - mở qua {GIAY_BAI_KHONG_BAT_BUOC}s", "NORMAL"

    # ----- Dự phòng: không có dữ liệu API -----
    name_lower = name_clean.lower()
    if re.search(r"trắc nghiệm kiểm tra|kiểm tra trắc nghiệm|tính điểm|phải đạt\s+\d+\s*\(?điểm\)?", name_lower):
        return 0, "Trắc nghiệm / bài tính điểm - phải tự làm", "QUIZ_SKIP"
    if "video" in name_lower:
        return 5 * 60 + SAFETY_BUFFER_SECONDS, "Dự phòng Video: 5 phút (hoặc theo độ dài video)", "NORMAL"
    if any(k in name_lower for k in ["bài đọc", "thảo luận", "khảo sát"]):
        return 2 * 60 + SAFETY_BUFFER_SECONDS, "Dự phòng Bài đọc/Thảo luận: 2 phút", "NORMAL"
    if any(k in name_lower for k in ["thông tin", "nhật ký", "reflection"]):
        return 1 * 60 + SAFETY_BUFFER_SECONDS, "Dự phòng Thông tin/Nhật ký: 1 phút", "NORMAL"
    if any(k in name_lower for k in ["pdf", "tài liệu", "đề cương", "giáo trình", "học liệu", "hướng dẫn", "danh mục"]):
        return DEFAULT_PDF_SECONDS, f"Dự phòng Tài liệu/PDF: {DEFAULT_PDF_SECONDS}s", "NORMAL"
    return 90, "Dự phòng mặc định: 90s", "NORMAL"


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
    """Trả về list (vi_tri, key, name, class) — key = tên + số thứ tự trùng tên,
    vì có bài trùng tên ở các chương khác nhau (vd 'Hoạt động 1: Thảo luận...').
    vi_tri = chỉ số trong querySelectorAll để bấm; bỏ qua mục rỗng (danh sách phụ của giao diện)."""
    ket_qua = []
    dem_trung = {}
    for vi_tri, (class_str, raw_text) in enumerate(driver.execute_script(JS_DANH_SACH_BAI)):
        name = " ".join((raw_text or "").split())
        if not name:
            continue
        dem_trung[name] = dem_trung.get(name, 0) + 1
        ket_qua.append((vi_tri, f"{name}#{dem_trung[name]}", name, class_str or ""))
    return ket_qua


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


def hop_thoai_dang_hoc(driver):
    """LMS định kỳ hỏi 'Bạn có đang học tập không?' — không bấm trong 10s là bị đá về trang chủ."""
    try:
        return driver.execute_script("""
            var p = document.querySelector('.swal2-popup');
            return !!(p && p.offsetParent !== null && /đang học/i.test(p.textContent));
        """)
    except Exception:
        return False


def dem_nguoc(driver, tong_so_giay, ten_bai):
    """
    Đếm ngược thời gian trực quan theo phút:giây, giữ video luôn phát.
    (LMS chỉ lưu thời gian học khi RỜI khỏi bài nên không chờ tích xanh ở đây.)
    Trả về False nếu bị LMS đá khỏi bài (không trả lời hộp thoại 'đang học').
    """
    start_time = time.time()
    last_interaction = start_time

    while True:
        elapsed = time.time() - start_time
        remaining = int(tong_so_giay - elapsed)
        if remaining <= 0:
            break

        # Hộp thoại "Bạn có đang học tập không?" -> báo người dùng tự bấm
        if hop_thoai_dang_hoc(driver):
            print("\n   🔔 LMS HỎI 'Bạn có đang học tập không?' -> BẤM 'CÓ' TRÊN CHROME TRONG 10 GIÂY!")
            for _ in range(10):
                if not hop_thoai_dang_hoc(driver):
                    break
                try:
                    import winsound
                    winsound.Beep(1200, 300)
                except Exception:
                    print("\a", end="", flush=True)
                time.sleep(0.7)

        # Bị đá khỏi lớp (không ai bấm 'Có') -> thời gian không được tính
        if "/learn/lop-hoc/" not in driver.current_url:
            print(f"\n   ⚠️ BỊ LMS ĐÁ KHỎI BÀI vì không trả lời hộp thoại -> treo lại: {ten_bai[:45]}")
            return False

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

        m_rem = remaining // 60
        s_rem = remaining % 60
        m_tot = tong_so_giay // 60
        s_tot = tong_so_giay % 60
        print(f"   ⏳ [TREO MÁY] Còn {m_rem:02d}:{s_rem:02d} / {m_tot:02d}:{s_tot:02d} | {ten_bai[:45]}...", end="\r", flush=True)
        time.sleep(1)

    print(f"\n   ⏱️ ĐỦ GIỜ: {ten_bai[:50]}")
    return True


def doc_bai_da_xong(driver, course_url):
    """Tập id các mục LMS đã ghi nhận hoàn thành (isFinish) — chính xác hơn icon trên giao diện."""
    m = re.search(r"chi-tiet/([0-9a-fA-F-]{36})", course_url)
    if not m:
        return set()
    try:
        res = driver.execute_async_script(JS_GOI_API, f"{API_LMS}/LmsClass/FrUserJoinClassNew/{m.group(1)}")
        ds = ((res or {}).get("data") or {}).get("listClassUserLearning") or []
        return {x["classContentId"] for x in ds if x.get("isFinish")}
    except Exception:
        return set()


def roi_khoi_bai(driver, vi_tri_hien_tai):
    """Bấm sang 1 bài đã xong khác để LMS lưu thời gian học của bài vừa treo."""
    try:
        driver.execute_script("""
            var ds = document.querySelectorAll('div.__lesson-status'), cur = arguments[0];
            var dich = -1;
            for (var i = 0; i < ds.length; i++) {
                var a = ds[i].parentElement.querySelector('a');
                if (i == cur || !a || !a.textContent.trim()) continue;
                if (ds[i].className.indexOf('ico-img-status-3') >= 0) { dich = i; break; }
                if (dich < 0) dich = i;  // lớp mới chưa có bài nào xong: bấm tạm bài khác
            }
            if (dich >= 0) ds[dich].parentElement.querySelector('a').click();
        """, vi_tri_hien_tai)
        time.sleep(5)
    except Exception:
        pass


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

    # Đọc thời gian tối thiểu / loại bài của TỪNG MỤC từ API LMS (dùng cho mọi môn)
    thong_tin = doc_thong_tin_lop(driver, tai_khoan["course_url"])
    if thong_tin:
        bat_buoc = [n for n in thong_tin.values() if n.get("isRequired") and n.get("mincore")
                    and "kiểm tra" not in ((n.get("type") or {}).get("title") or "").lower()]
        print(f"📋 Đọc được {len(thong_tin)} mục từ LMS: {len(bat_buoc)} bài bắt buộc có thời gian tối thiểu "
              f"(tổng {sum(float(n['mincore']) for n in bat_buoc):.0f} phút)")
    else:
        print("⚠️ Không đọc được thông tin lớp từ LMS, dùng thời gian dự phòng theo tên bài.")

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
        da_xong_api = doc_bai_da_xong(driver, tai_khoan["course_url"]) if thong_tin else set()
        so_hoan_thanh = 0
        danh_sach_chua_xong = []

        for vi_tri, key, name, class_str in danh_sach:
            if "ico-img-status-3" in class_str or (thong_tin.get(key) or {}).get("id") in da_xong_api:
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
        info = thong_tin.get(key)
        so_giay, ly_do, loai_bai = xac_dinh_thoi_gian_hoc(ten_bai, info)

        # Bài kiểm tra / bài tập: bỏ qua, cuối cùng báo để tự làm
        if loai_bai == "QUIZ_SKIP":
            print(f"\n⏭️ [BỎ QUA] {ten_bai} ({ly_do})")
            bo_qua[key] = (ten_bai, ly_do)
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

        # Không có dữ liệu LMS mà bài có video -> treo theo độ dài video
        if not info:
            dur = thoi_luong_video(driver)
            if dur and dur + SAFETY_BUFFER_SECONDS > so_giay:
                so_giay = dur + SAFETY_BUFFER_SECONDS
                ly_do = f"Theo độ dài video: {dur // 60}:{dur % 60:02d} (+{SAFETY_BUFFER_SECONDS}s buffer)"
        print(f"   📊 Căn cứ thời gian: {ly_do}")

        if dem_nguoc(driver, so_giay, ten_bai):
            so_lan_thu[key] = so_lan_thu.get(key, 0) + 1
            roi_khoi_bai(driver, muc_tieu["vi_tri"])
            print("🔄 Chuyển sang bài tiếp theo...\n")
        else:
            driver.get(tai_khoan["course_url"])
            cho_danh_sach_bai(driver, tai_khoan["course_url"])
