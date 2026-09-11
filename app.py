import streamlit as st
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import sqlite3

# Configure the page layout
st.set_page_config(page_title="Scheduling Dashboard", layout="wide")

# Custom CSS to ensure short events (like 15-min slots) are tall enough to read
st.markdown("""
    <style>
    .fc-event {
        min-height: 24px !important;
        font-size: 0.85em !important;
        padding: 2px 4px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Local SQLite Database
def init_db():
    conn = sqlite3.connect("scheduler.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT,
            start_time TEXT,
            end_time TEXT,
            category TEXT,
            color TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Database Helper Functions
def get_all_events():
    conn = sqlite3.connect("scheduler.db")
    c = conn.cursor()
    c.execute("SELECT id, title, start_time, end_time, category, color FROM events")
    rows = c.fetchall()
    conn.close()
    
    events = []
    for row in rows:
        events.append({
            "id": row[0],
            "title": row[1],
            "start": row[2],
            "end": row[3],
            "category": row[4],
            "backgroundColor": row[5],
            "allDay": False
        })
    return events

def add_event_to_db(event):
    conn = sqlite3.connect("scheduler.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO events (id, title, start_time, end_time, category, color) VALUES (?, ?, ?, ?, ?, ?)",
              (event["id"], event["title"], event["start"], event["end"], event["category"], event["backgroundColor"]))
    conn.commit()
    conn.close()

def delete_event_from_db(event_id):
    conn = sqlite3.connect("scheduler.db")
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

st.title("Scheduling Dashboard")

# Define categories with updated, highly-visible colors and dots
CATEGORY_INFO = {
    "🔴 Work": {"name": "Work", "color": "#FF4B4B", "dot": "🔴"},
    "🔵 Personal": {"name": "Personal", "color": "#1E88E5", "dot": "🔵"},  # Bright Royal Blue
    "🟠 Urgent": {"name": "Urgent", "color": "#FFA15A", "dot": "🟠"},
    "🟢 Health & Fitness": {"name": "Health & Fitness", "color": "#00CC96", "dot": "🟢"}
}

# Fetch current events from SQLite
all_events = get_all_events()

# Sidebar Interface
with st.sidebar:
    st.header("Add New Event")
    with st.form("add_event_form", clear_on_submit=True):
        event_title = st.text_input("Event Title", placeholder="e.g., Team Sync")
        selected_category_key = st.selectbox("Category", options=list(CATEGORY_INFO.keys()))
        event_date = st.date_input("Event Date")
        start_time = st.time_input("Start Time")
        end_time = st.time_input("End Time")
        
        recurrence = st.selectbox(
            "Recurrence", 
            options=["None", "Daily", "Weekly", "Indefinitely (Daily - 1 Year)", "Indefinitely (Weekly - 1 Year)"]
        )
        
        if recurrence in ["Daily", "Weekly"]:
            recurrence_count = st.number_input("Repeat Count (Times)", min_value=1, max_value=365, value=7)
        else:
            recurrence_count = 1
        
        submitted = st.form_submit_button("Save to Calendar")

        if submitted and event_title:
            cat_data = CATEGORY_INFO[selected_category_key]
            assigned_color = cat_data["color"]
            category_name = cat_data["name"]
            dot_symbol = cat_data["dot"]
            
            base_start_dt = datetime.combine(event_date, start_time)
            base_end_dt = datetime.combine(event_date, end_time)
            
            if recurrence == "Daily":
                freq = "Daily"
                occurrences = recurrence_count
            elif recurrence == "Weekly":
                freq = "Weekly"
                occurrences = recurrence_count
            elif recurrence == "Indefinitely (Daily - 1 Year)":
                freq = "Daily"
                occurrences = 365
            elif recurrence == "Indefinitely (Weekly - 1 Year)":
                freq = "Weekly"
                occurrences = 52
            else:
                freq = "None"
                occurrences = 1

            timestamp_base = datetime.now().timestamp()
            
            for i in range(occurrences):
                if freq == "Daily":
                    curr_start = base_start_dt + timedelta(days=i)
                    curr_end = base_end_dt + timedelta(days=i)
                elif freq == "Weekly":
                    curr_start = base_start_dt + timedelta(weeks=i)
                    curr_end = base_end_dt + timedelta(weeks=i)
                else:
                    curr_start = base_start_dt
                    curr_end = base_end_dt
                
                event_id = f"{timestamp_base}_{i}"
                new_event = {
                    "id": event_id,
                    "title": f"{dot_symbol} {event_title}",
                    "start": curr_start.strftime("%Y-%m-%dT%H:%M:%S"),
                    "end": curr_end.strftime("%Y-%m-%dT%H:%M:%S"),
                    "backgroundColor": assigned_color,
                    "category": category_name
                }
                add_event_to_db(new_event)
                
            st.success("Event(s) added successfully!")
            st.rerun()

    st.divider()

    # Delete Section
    st.header("Delete Event")
    if all_events:
        event_options = {f"{e['title']} ({e['start'][:10]})": e['id'] for e in all_events}
        selected_event_label = st.selectbox("Select Event to Remove", options=list(event_options.keys()))
        
        if st.button("Delete Selected Event", type="primary"):
            target_id = event_options[selected_event_label]
            delete_event_from_db(target_id)
            st.success("Event deleted!")
            st.rerun()
    else:
        st.info("No events available to delete.")

    st.divider()

    # Search Bar & Category Filters
    st.header("Filters")
    search_query = st.text_input("Search Events", placeholder="Type keyword...")
    
    category_names = [cat["name"] for cat in CATEGORY_INFO.values()]
    selected_filters = st.multiselect(
        "Filter Categories",
        options=category_names,
        default=category_names
    )

# Apply Filters and Search to Events List
filtered_events = all_events
if selected_filters:
    filtered_events = [e for e in filtered_events if e["category"] in selected_filters]
if search_query:
    filtered_events = [e for e in filtered_events if search_query.lower() in e["title"].lower()]

# Configure the calendar layout
calendar_options = {
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,timeGridDay",
    },
    "initialView": "dayGridMonth",
    "selectable": True,
    "eventMinHeight": 25,
}

# Render the calendar component
calendar_widget = calendar(events=filtered_events, options=calendar_options)