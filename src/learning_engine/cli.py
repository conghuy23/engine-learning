from __future__ import annotations  # Hỗ trợ kiểu dữ liệu hiện đại

import time  # Thư viện đo thời gian (dùng để tính thời gian trả lời thẻ)
from datetime import datetime, timezone  # Xử lý ngày giờ

import typer  # Thư viện tạo CLI
from rich.console import Console  # Thư viện tạo giao diện terminal đẹp
from rich.panel import Panel  # Tạo khung viền
from rich.prompt import Prompt  # Tạo ô nhập liệu đẹp
from sqlalchemy import func, select  # Thư viện truy vấn database

from .config import settings  # Lấy cài đặt
from .db import get_session, init_db  # Lấy hàm kết nối DB
from .integrations.anki import AnkiClient, AnkiError, push_cards  # Lấy code từ Phase 5
from .models import Card, Concept, ReviewLog, Topic  # Lấy các models
from .services import feynman as feynman_svc  # Lấy service Feynman
from .services.interleaving import build_session  # Lấy service Interleaving
from .services.scheduler import due_cards, review_card  # Lấy service Scheduler

app = typer.Typer(help="Learning-retention engine")  # Khởi tạo ứng dụng CLI
console = Console()  # Khởi tạo đối tượng in màn hình

# Tạo các nhóm lệnh con
topic_app = typer.Typer(help="Quản lý chủ đề")
concept_app = typer.Typer(help="Quản lý khái niệm")
card_app = typer.Typer(help="Quản lý thẻ")
anki_app = typer.Typer(help="Tích hợp Anki")

# Gắn các nhóm lệnh vào ứng dụng chính
app.add_typer(topic_app, name="topic")
app.add_typer(concept_app, name="concept")
app.add_typer(card_app, name="card")
app.add_typer(anki_app, name="anki")

@app.command()
def init():
    """Tạo database."""
    init_db()  # Gọi hàm tạo bảng trong db.py
    console.print("[green]Database đã được khởi tạo.[/green]")  # In chữ màu xanh

# ---------- NHÓM LỆNH TOPIC ----------
@topic_app.command("add")
def topic_add(name: str, description: str = ""):  # Lệnh: learn topic add "Tên"
    with get_session() as s:  # Mở phiên làm việc với DB
        t = Topic(name=name, description=description or None)  # Tạo đối tượng Topic mới
        s.add(t)  # Thêm vào phiên
        s.flush()  # Lưu tạm để lấy ID
        console.print(f"[green]Đã tạo Topic #{t.id}[/green] {t.name}")

@topic_app.command("list")
def topic_list():
    with get_session() as s:
        for t in s.scalars(select(Topic).order_by(Topic.name)):  # Lấy tất cả Topic, sắp xếp theo tên
            n = s.scalar(select(func.count(Concept.id)).where(Concept.topic_id == t.id))  # Đếm số concept
            console.print(f"[cyan]#{t.id}[/cyan] {t.name}  ({n} concepts)")

# ---------- NHÓM LỆNH CONCEPT ----------
@concept_app.command("add")
def concept_add(topic_id: int, title: str, content: str = ""):  # Lệnh: learn concept add 1 "Tên"
    with get_session() as s:
        c = Concept(topic_id=topic_id, title=title, content=content or None)
        s.add(c)
        s.flush()
        console.print(f"[green]Đã tạo Concept #{c.id}[/green] {c.title}")

# ---------- NHÓM LỆNH CARD ----------
@card_app.command("add")
def card_add(concept_id: int, front: str, back: str):  # Lệnh: learn card add 1 "Mặt trước" "Mặt sau"
    with get_session() as s:
        c = Card(concept_id=concept_id, front=front, back=back)
        s.add(c)
        s.flush()
        console.print(f"[green]Đã tạo Card #{c.id}[/green]")

# ---------- LỆNH REVIEW (ÔN TẬP) ----------
@app.command()
def review(limit: int = 20):  # Lệnh: learn review
    """Phiên ôn tập xen kẽ (Interleaved) + Gợi nhớ chủ động (Active Recall)."""
    with get_session() as s:
        cards = build_session(s, limit=limit)  # Lấy danh sách thẻ đã được trộn (từ Phase 4)
        if not cards:
            console.print("[yellow]Không có thẻ nào đến hạn. 🎉[/yellow]")
            return

        console.print(f"[bold]Phiên ôn tập: {len(cards)} thẻ, đã trộn chủ đề[/bold]\n")

        for i, card in enumerate(cards, 1):  # Lặp qua từng thẻ
            topic = card.concept.topic.name  # Lấy tên chủ đề
            console.print(  # In khung chứa câu hỏi
                Panel(
                    card.front,  # Nội dung mặt trước
                    title=f"{i}/{len(cards)}  ·  [magenta]{topic}[/magenta]  ·  {card.concept.title}",
                    border_style="blue",
                )
            )
            start = time.perf_counter()  # Bắt đầu tính giờ
            Prompt.ask("[dim]Hãy trả lời trong đầu, sau đó nhấn Enter[/dim]", default="")  # Chờ người dùng Enter
            console.print(Panel(card.back, title="Đáp án", border_style="green"))  # Hiện đáp án

            q = int(  # Yêu cầu người dùng đánh giá chất lượng câu trả lời
                Prompt.ask(
                    "Chấm điểm 0-5 [red]0-2 (quên)[/red] / [green]4 (tốt)[/green] / [cyan]5 (dễ)[/cyan]",
                    choices=["0", "1", "2", "3", "4", "5"],
                    default="4",
                )
            )
            duration = int((time.perf_counter() - start) * 1000)  # Tính thời gian trả lời (mili giây)
            review_card(s, card, q, duration_ms=duration)  # Gọi hàm cập nhật lịch (từ Phase 4)
            console.print()

        console.print("[bold green]Hoàn thành phiên ôn tập.[/bold green]")

# ---------- LỆNH FEYNMAN ----------
@app.command()
def feynman(concept_id: int):  # Lệnh: learn feynman 1
    """Viết giải thích bằng ngôn ngữ đơn giản; máy sẽ tìm ra lỗ hổng."""
    with get_session() as s:
        c = s.get(Concept, concept_id)  # Tìm concept theo ID
        if not c:
            console.print("[red]Không tìm thấy concept[/red]")
            raise typer.Exit(1)

        console.print(Panel(c.title, title="Hãy giải thích khái niệm này bằng tiếng Việt đơn giản"))
        text = Prompt.ask("[dim]Bài giải thích của bạn[/dim]")  # Nhập bài giải thích

        result = feynman_svc.save_explanation(s, c, text)  # Gọi service phân tích (từ Phase 4)
        if result.gaps:  # Nếu tìm thấy lỗ hổng
            console.print("\n[bold yellow]Phát hiện lỗ hổng:[/bold yellow]")
            for g in result.gaps:
                console.print(f"  • {g}")
            if typer.confirm("Tạo thẻ ghi nhớ cho các lỗ hổng này?", default=True):  # Hỏi có muốn tạo thẻ không
                cards = feynman_svc.gaps_to_cards(s, c)
                console.print(f"[green]Đã tạo {len(cards)} thẻ.[/green]")
        else:
            console.print("[green]Không phát hiện lỗ hổng rõ ràng. Bài giải thích rất tốt.[/green]")

# ---------- NHÓM LỆNH ANKI ----------
@anki_app.command("push")
def anki_push(limit: int = 100):  # Lệnh: learn anki push
    """Đẩy các thẻ chưa đồng bộ sang Anki."""
    client = AnkiClient(settings.anki_url)  # Kết nối tới Anki
    with get_session() as s:
        # Tìm các thẻ chưa có anki_note_id (chưa đẩy lên Anki)
        cards = list(s.scalars(select(Card).where(Card.anki_note_id.is_(None)).limit(limit)))
        try:
            n = push_cards(client, cards, deck=settings.anki_deck, model=settings.anki_model)
        except AnkiError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]Đã đẩy {n} thẻ sang bộ thẻ '{settings.anki_deck}'.[/green]")

@anki_app.command("sync")
def anki_sync():  # Lệnh: learn anki sync
    try:
        AnkiClient(settings.anki_url).sync()
        console.print("[green]Đã kích hoạt đồng bộ Anki.[/green]")
    except AnkiError as e:
        console.print(f"[red]{e}[/red]")

# ---------- LỆNH STATS (THỐNG KÊ) ----------
@app.command()
def stats():  # Lệnh: learn stats
    with get_session() as s:
        now = datetime.now(timezone.utc)
        total = s.scalar(select(func.count(Card.id))) or 0  # Tổng số thẻ
        due = s.scalar(select(func.count(Card.id)).where(Card.due_at <= now)) or 0  # Số thẻ đến hạn
        reviews = s.scalar(select(func.count(ReviewLog.id))) or 0  # Tổng số lần ôn tập
        avg_q = s.scalar(select(func.avg(ReviewLog.quality))) or 0.0  # Điểm trung bình

    console.print(  # In khung thống kê
        Panel(
            f"Tổng số thẻ: [cyan]{total}[/cyan]\n"
            f"Đến hạn ôn: [yellow]{due}[/yellow]\n"
            f"Tổng số lần ôn: [cyan]{reviews}[/cyan]\n"
            f"Điểm trung bình: [green]{avg_q:.2f}[/green]",
            title="Thống kê",
        )
    )

if __name__ == "__main__":
    app()  # Cho phép chạy trực tiếp file này bằng lệnh python cli.py