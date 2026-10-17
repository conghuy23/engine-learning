import streamlit as st
from datetime import datetime, timezone
from sqlalchemy import select, func

# Import code từ dự án của bạn
from learning_engine.db import get_session, init_db, SessionLocal
from learning_engine.models import Topic, Concept, Card
from learning_engine.services.scheduler import review_card
from learning_engine.services.interleaving import build_session
from learning_engine.integrations.anki import AnkiClient, push_cards, AnkiError

# Cấu hình giao diện web
st.set_page_config(page_title="Learning Engine", page_icon="🧠", layout="wide")

# Khởi tạo database nếu chưa có
init_db()

# Tạo thanh menu bên trái
st.sidebar.title("🧠 Learning Engine")
menu = st.sidebar.radio("Chọn chức năng:", ["📚 Ôn tập (Review)", "➕ Thêm dữ liệu", "📊 Thống kê", "🔄 Đồng bộ Anki"])

# Hàm hỗ trợ lấy session database
def get_db():
    return SessionLocal()

# ==========================================
# CHỨC NĂNG 1: ÔN TẬP (REVIEW)
# ==========================================
if menu == "📚 Ôn tập (Review)":
    st.header("Phiên ôn tập (Interleaved)")
    
    # Khởi tạo state cho phiên ôn tập
    if 'current_card' not in st.session_state:
        st.session_state.current_card = None
    if 'show_answer' not in st.session_state:
        st.session_state.show_answer = False

    db = get_db()
    
    # Nút bắt đầu/load thẻ mới
    if st.button("Lấy thẻ tiếp theo 🔄") or st.session_state.current_card is None:
        cards = build_session(db, limit=1)
        if cards:
            st.session_state.current_card = cards[0]
            st.session_state.show_answer = False
        else:
            st.session_state.current_card = None
            st.success("🎉 Tuyệt vời! Bạn đã hoàn thành tất cả thẻ đến hạn hôm nay.")

    # Hiển thị thẻ
    if st.session_state.current_card:
        card = st.session_state.current_card
        
        # Hiển thị chủ đề và câu hỏi
        st.info(f"**Chủ đề:** {card.concept.topic.name} | **Khái niệm:** {card.concept.title}")
        st.markdown(f"### ❓ {card.front}")
        
        # Nút xem đáp án
        if not st.session_state.show_answer:
            if st.button("Xem đáp án 👀", type="primary"):
                st.session_state.show_answer = True
                st.rerun()
        
        # Hiển thị đáp án và nút chấm điểm
        if st.session_state.show_answer:
            st.markdown(f"### ✅ {card.back}")
            st.write("---")
            st.write("**Bạn nhớ thẻ này tốt đến mức nào?**")
            
            col1, col2, col3, col4 = st.columns(4)
            
            def submit_review(quality):
                # Cập nhật vào DB bằng thuật toán SM-2
                review_card(db, card, quality)
                db.commit()
                st.session_state.current_card = None # Reset để lấy thẻ mới
                st.rerun()

            with col1:
                st.button("Quên (0-2)", on_click=submit_review, args=(1,), type="primary", use_container_width=True)
            with col2:
                st.button("Khó (3)", on_click=submit_review, args=(3,), use_container_width=True)
            with col3:
                st.button("Tốt (4)", on_click=submit_review, args=(4,), use_container_width=True)
            with col4:
                st.button("Dễ (5)", on_click=submit_review, args=(5,), use_container_width=True)

# ==========================================
# CHỨC NĂNG 2: THÊM DỮ LIỆU
# ==========================================
elif menu == "➕ Thêm dữ liệu":
    st.header("Quản lý Dữ liệu")
    db = get_db()
    
    tab1, tab2, tab3 = st.tabs(["Thêm Chủ đề", "Thêm Khái niệm", "Thêm Thẻ"])
    
    with tab1:
        st.subheader("Tạo Chủ đề mới")
        topic_name = st.text_input("Tên chủ đề:")
        topic_desc = st.text_area("Mô tả (không bắt buộc):")
        if st.button("Tạo Chủ đề"):
            if topic_name:
                t = Topic(name=topic_name, description=topic_desc)
                db.add(t)
                db.commit()
                st.success(f"Đã tạo chủ đề: {topic_name}")
            else:
                st.error("Vui lòng nhập tên chủ đề")

    with tab2:
        st.subheader("Tạo Khái niệm mới")
        topics = db.scalars(select(Topic)).all()
        if topics:
            topic_options = {t.name: t.id for t in topics}
            selected_topic = st.selectbox("Chọn chủ đề:", list(topic_options.keys()))
            concept_title = st.text_input("Tên khái niệm:")
            concept_content = st.text_area("Nội dung chi tiết:")
            if st.button("Tạo Khái niệm"):
                if concept_title:
                    c = Concept(topic_id=topic_options[selected_topic], title=concept_title, content=concept_content)
                    db.add(c)
                    db.commit()
                    st.success(f"Đã tạo khái niệm: {concept_title}")
        else:
            st.warning("Hãy tạo ít nhất 1 chủ đề trước.")

    with tab3:
        st.subheader("Tạo Thẻ ghi nhớ (Flashcard)")
        concepts = db.scalars(select(Concept)).all()
        if concepts:
            concept_options = {f"{c.title} (Topic: {c.topic.name})": c.id for c in concepts}
            selected_concept = st.selectbox("Chọn khái niệm:", list(concept_options.keys()))
            card_front = st.text_area("Mặt trước (Câu hỏi):")
            card_back = st.text_area("Mặt sau (Đáp án):")
            if st.button("Tạo Thẻ"):
                if card_front and card_back:
                    card = Card(concept_id=concept_options[selected_concept], front=card_front, back=card_back)
                    db.add(card)
                    db.commit()
                    st.success("Đã tạo thẻ mới!")
        else:
            st.warning("Hãy tạo ít nhất 1 khái niệm trước.")

# ==========================================
# CHỨC NĂNG 3: THỐNG KÊ
# ==========================================
elif menu == "📊 Thống kê":
    st.header("Thống kê Hệ thống")
    db = get_db()
    
    total_cards = db.scalar(select(func.count(Card.id))) or 0
    now = datetime.now(timezone.utc)
    due_cards = db.scalar(select(func.count(Card.id)).where(Card.due_at <= now)) or 0
    
    col1, col2 = st.columns(2)
    col1.metric("Tổng số thẻ", total_cards)
    col2.metric("Thẻ cần ôn hôm nay", due_cards)

# ==========================================
# CHỨC NĂNG 4: ĐỒNG BỘ ANKI
# ==========================================
elif menu == "🔄 Đồng bộ Anki":
    st.header("Đồng bộ với Anki")
    st.write("Đảm bảo phần mềm Anki đang mở và đã cài AnkiConnect.")
    
    if st.button("Đẩy thẻ chưa đồng bộ lên Anki"):
        db = get_db()
        unsynced_cards = db.scalars(select(Card).where(Card.anki_note_id.is_(None))).all()
        
        if not unsynced_cards:
            st.info("Không có thẻ nào cần đồng bộ.")
        else:
            try:
                client = AnkiClient("http://localhost:8765")
                count = push_cards(client, unsynced_cards, deck="Learning Engine", model="Basic")
                db.commit()
                st.success(f"Đã đẩy thành công {count} thẻ lên Anki!")
            except AnkiError as e:
                st.error(f"Lỗi kết nối Anki: {e}")