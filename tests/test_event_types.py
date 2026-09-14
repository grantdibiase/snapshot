import unittest
from src.event_types import event_type, EVENT_TYPES
from src.calendar_builder import format_event_for_google
class CalendarTests(unittest.TestCase):
    def test_each_category_has_distinct_calendar_color(self):
        colors=[]
        for kind in EVENT_TYPES:
            body=format_event_for_google({'title':'Test','type':kind,'date':'2026-09-14'})
            colors.append(body['colorId'])
        self.assertEqual(len(colors),len(set(colors)))
    def test_legacy_classes_are_classified(self):
        for title,expected in [('CS 382 Lab','lab'),('CS 385 Recitation','recitation'),('Math midterm','exam'),('CS 385','lecture')]:
            self.assertEqual(event_type({'title':title,'type':'class'}),expected)
    def test_first_class_not_before_semester(self):
        body=format_event_for_google({'title':'Test','days':['Monday'],'start_time':'9:00 AM','end_time':'10:00 AM','semester_start':'2026-09-16','semester_end':'2026-12-15'})
        self.assertTrue(body['start']['dateTime'].startswith('2026-09-21'))
    def test_all_day_exclusive_end(self):
        body=format_event_for_google({'title':'Test','date':'2026-09-14'})
        self.assertEqual(body['end']['date'],'2026-09-15')
