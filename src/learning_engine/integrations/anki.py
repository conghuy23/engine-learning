from __future__ import annotations  # Cho phép sử dụng các kiểu dữ liệu hiện đại trong Python cũ

import httpx  # Thư viện dùng để gửi HTTP request (gọi API) tới Anki

from ..models import Card  # Import model Card từ thư mục models để dùng làm kiểu dữ liệu


class AnkiError(RuntimeError):  # Tạo một lớp lỗi riêng để dễ dàng bắt lỗi khi kết nối Anki thất bại
    pass  # Không cần thêm code gì, chỉ cần kế thừa từ RuntimeError


class AnkiClient:  # Tạo class quản lý các kết nối tới Anki
    def __init__(self, url: str = "http://localhost:8765", version: int = 6):
        self.url = url  # Lưu địa chỉ API của AnkiConnect
        self.version = version  # Lưu phiên bản API (AnkiConnect hiện tại dùng version 6)

    def invoke(self, action: str, **params):  # Hàm lõi để gửi lệnh tới Anki
        payload = {"action": action, "version": self.version, "params": params}  # Đóng gói lệnh thành JSON
        try:
            r = httpx.post(self.url, json=payload, timeout=10)  # Gửi POST request tới Anki, chờ tối đa 10s
            r.raise_for_status()  # Nếu Anki trả về lỗi HTTP (vd: 404, 500), ném ra ngoại lệ
        except httpx.HTTPError as e:  # Bắt lỗi nếu không kết nối được (vd: Anki chưa mở)
            raise AnkiError(f"Không thể kết nối AnkiConnect tại {self.url}: {e}") from e  # Báo lỗi rõ ràng

        data = r.json()  # Chuyển kết quả Anki trả về thành dictionary
        if data.get("error"):  # Nếu Anki báo lỗi trong nội dung trả về
            raise AnkiError(data["error"])  # Ném lỗi đó ra ngoài
        return data["result"]  # Trả về kết quả thành công

    # --- Các hàm tiện ích bậc cao ---
    def ensure_deck(self, deck: str) -> None:  # Đảm bảo bộ thẻ (deck) đã tồn tại trên Anki
        self.invoke("createDeck", deck=deck)  # Gọi lệnh tạo deck (nếu có rồi Anki sẽ bỏ qua)

    def add_note(self, *, deck: str, model: str, front: str, back: str, tags=None) -> int:  # Thêm 1 thẻ mới
        return self.invoke(  # Gọi lệnh thêm thẻ
            "addNote",  # Tên lệnh của AnkiConnect
            note={  # Dữ liệu của thẻ
                "deckName": deck,  # Tên bộ thẻ
                "modelName": model,  # Tên mẫu thẻ (vd: Basic)
                "fields": {"Front": front, "Back": back},  # Nội dung mặt trước/mặt sau
                "tags": tags or ["learning-engine"],  # Gắn tag để dễ quản lý trên Anki
                "options": {"allowDuplicate": False},  # Không cho phép tạo thẻ trùng lặp
            },
        )

    def sync(self) -> None:  # Đồng bộ dữ liệu Anki lên server (AnkiWeb) hoặc các thiết bị khác
        self.invoke("sync")  # Gọi lệnh sync


def push_cards(client: AnkiClient, cards: list[Card], *, deck: str, model: str) -> int:  # Hàm đẩy nhiều thẻ cùng lúc
    client.ensure_deck(deck)  # Đảm bảo deck đã có
    pushed = 0  # Biến đếm số thẻ đã đẩy thành công
    for c in cards:  # Lặp qua từng thẻ trong danh sách
        if c.anki_note_id:  # Nếu thẻ này đã được đẩy lên Anki trước đó rồi
            continue  # Thì bỏ qua, không đẩy lại
        note_id = client.add_note(deck=deck, model=model, front=c.front, back=c.back)  # Đẩy thẻ lên
        c.anki_note_id = note_id  # Lưu lại ID của thẻ trên Anki vào database của mình
        pushed += 1  # Tăng biến đếm
    return pushed  # Trả về tổng số thẻ đã đẩy