import unittest
from unittest.mock import patch, MagicMock, call, ANY
import numpy as np
import cv2 # For type hints and constants if necessary
import os
import sys
import unicodedata # Used by is_japanese_char, so ensure it's available

# Adjust path to import module from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/extract_serif')))
from balloon import Balloons, is_japanese_char, Koma 
# JOYO_KANJI is imported by balloon.py, so it should be available if balloon.py is loaded

# Helper to create a mock image (numpy array)
def create_mock_image_data(height, width, channels=3, dtype=np.uint8, fill_value=0):
    if channels == 1:
        shape = (height, width)
    else:
        shape = (height, width, channels)
    return np.full(shape, fill_value, dtype=dtype)

class TestBalloonModuleFunctions(unittest.TestCase):
    def test_is_japanese_char(self):
        self.assertTrue(is_japanese_char("日")) # Kanji
        self.assertTrue(is_japanese_char("あ")) # Hiragana
        self.assertTrue(is_japanese_char("ア")) # Katakana
        self.assertTrue(is_japanese_char("。")) # Punctuation (Mark)
        self.assertTrue(is_japanese_char("…")) # Horizontal Ellipsis
        self.assertFalse(is_japanese_char("A")) # Latin
        self.assertFalse(is_japanese_char("1")) # Digit
        self.assertFalse(is_japanese_char(" ")) # Space
        self.assertFalse(is_japanese_char("Ç")) # Latin-1 Supplement

class TestKoma(unittest.TestCase):
    @patch('cv2.imread')
    def test_koma_initialization(self, mock_cv_imread):
        mock_img = create_mock_image_data(100, 100)
        mock_cv_imread.return_value = mock_img
        
        koma = Koma("dummy_path.png")
        self.assertEqual(koma.img_path, "dummy_path.png")
        self.assertIsNotNone(koma.img)
        self.assertEqual(koma.img_height, 100)
        self.assertEqual(koma.img_width, 100)
        mock_cv_imread.assert_called_once_with("dummy_path.png")

    @patch('cv2.imread')
    def test_koma_initialization_image_not_found(self, mock_cv_imread):
        mock_cv_imread.return_value = None
        koma = Koma("nonexistent_path.png")
        self.assertEqual(koma.img_path, "nonexistent_path.png")
        self.assertIsNone(koma.img)
        # Check that height and width are not set or are defaults if img is None
        self.assertFalse(hasattr(koma, 'img_height'))
        self.assertFalse(hasattr(koma, 'img_width'))


class TestBalloons(unittest.TestCase):
    def setUp(self):
        # Mock amane_cut.args which might be used if utils.py is shared
        # For balloon.py, it uses its own constants mostly.
        # We need to mock cv2.imread because Balloons inherits from Koma
        with patch('cv2.imread', return_value=create_mock_image_data(1000, 800)) as mock_read:
            self.balloons = Balloons("dummy_img_path.png")
        
        # Ensure these attributes are set on the instance for is_good_ta
        self.balloons.img_height = 1000
        self.balloons.img_width = 800
        
        # Constants from balloon.py, can be overridden in specific tests
        self.balloons.NG_HEIGHT_RATIO = 0.03
        self.balloons.NG_LONG_WIDTH_RATIO = 1.3


    def test_text_replace(self):
        self.assertEqual(self.balloons._text_replace("かーか"), "カ-カ") # Test multiple replacements
        self.assertEqual(self.balloons._text_replace("テスト"), "テスト") # No replacement

    def test_define_rect(self):
        positions = [
            {"x": 10, "y": 20}, {"x": 60, "y": 20},
            {"x": 60, "y": 80}, {"x": 10, "y": 80}
        ]
        rect = self.balloons._define_rect(positions)
        self.assertEqual(rect, [10, 20, 50, 60]) # x, y, w, h

        positions_missing_xy = [
            {}, {"x": 50}, {}, {"y": 70}
        ]
        rect_missing = self.balloons._define_rect(positions_missing_xy)
        # lt.x=0, lt.y=0, rt.x=50, rt.y=0 (from lt), lb.x=0 (from lt), lb.y=70
        # w = 50-0=50, h = 70-0=70
        self.assertEqual(rect_missing, [0, 0, 50, 70])


    def test_get_ta_value(self):
        text_annotation = {
            "description": "テスト\n文",
            "boundingPoly": {
                "vertices": [
                    {"x": 10, "y": 20}, {"x": 60, "y": 20},
                    {"x": 60, "y": 80}, {"x": 10, "y": 80}
                ]
            }
        }
        expected_value = {
            "rect": [10, 20, 50, 60],
            "text": "テスト文" # Newline removed, no replacement in this case
        }
        self.assertEqual(self.balloons.get_ta_value(text_annotation), expected_value)

    def test_detect_laped(self):
        ta1 = {"rect": [10, 10, 50, 50]} # x,y,w,h
        ta2 = {"rect": [30, 30, 50, 50]} # Overlaps with ta1
        ta3 = {"rect": [100, 100, 50, 50]} # No overlap with ta1
        ta4 = {"rect": [0, 0, 70, 70]} # Contains ta1
        ta5 = {"rect": [20, 20, 20, 20]} # Contained by ta1

        self.assertTrue(self.balloons._detect_laped(ta1, ta2))
        self.assertFalse(self.balloons._detect_laped(ta1, ta3))
        self.assertTrue(self.balloons._detect_laped(ta1, ta4)) # ta4 contains ta1
        self.assertTrue(self.balloons._detect_laped(ta4, ta1)) # ta1 is contained by ta4
        self.assertTrue(self.balloons._detect_laped(ta1, ta5)) # ta5 is contained by ta1
        self.assertTrue(self.balloons._detect_laped(ta5, ta1)) # ta1 contains ta5

    def test_is_good_ta(self):
        # Setup img dimensions for is_good_ta
        self.balloons.img_height = 1000
        self.balloons.img_width = 800

        # Good TA
        good_ta_dict = {
            "description": "良い", 
            "boundingPoly": {"vertices": [{"x":100,"y":100},{"x":150,"y":100},{"x":150,"y":150},{"x":100,"y":150}]}
        }
        self.assertTrue(self.balloons.is_good_ta(good_ta_dict))

        # NG Word
        ng_word_ta = {**good_ta_dict, "description": "UFO"}
        self.assertFalse(self.balloons.is_good_ta(ng_word_ta))

        # Regex NG Match (e.g., only numbers)
        regex_ng_ta = {**good_ta_dict, "description": "123"}
        self.assertFalse(self.balloons.is_good_ta(regex_ng_ta))
        
        # Regex NG Match (e.g., only symbols)
        regex_ng_symbols_ta = {**good_ta_dict, "description": "%:;"}
        self.assertFalse(self.balloons.is_good_ta(regex_ng_symbols_ta))

        # Single non-Japanese char
        non_jp_char_ta = {**good_ta_dict, "description": "Q"}
        self.assertFalse(self.balloons.is_good_ta(non_jp_char_ta))

        # Non-Joyo Kanji
        non_joyo_ta = {**good_ta_dict, "description": "﨑"}
        self.assertFalse(self.balloons.is_good_ta(non_joyo_ta))

        # Too small height
        small_h_vertices = [{"x":100,"y":100},{"x":110,"y":100},{"x":110,"y":100 + self.balloons.img_height * 0.01},{"x":100,"y":100 + self.balloons.img_height * 0.01}]
        small_h_ta = {"description": "小", "boundingPoly": {"vertices": small_h_vertices}}
        self.assertFalse(self.balloons.is_good_ta(small_h_ta))
        
        # Small height but in SKIP_SIZE_EVAL_LIST
        skip_small_h_ta = {**small_h_ta, "description": "!"}
        self.assertTrue(self.balloons.is_good_ta(skip_small_h_ta)) # Should pass due to skip list

        # Too long width
        long_w_vertices = [{"x":100,"y":100},{"x":300,"y":100},{"x":300,"y":150},{"x":100,"y":150}] # w=200, h=50
        long_w_ta = {"description": "横長", "boundingPoly": {"vertices": long_w_vertices}}
        self.balloons.NG_LONG_WIDTH_RATIO = 2.0 # area_width (200) > area_height (50) * 2.0 = 100 => True
        self.assertFalse(self.balloons.is_good_ta(long_w_ta))

        # Long width but in SKIP_LONG_WIDTH_LIST
        skip_long_w_ta = {**long_w_ta, "description": "一"}
        self.assertTrue(self.balloons.is_good_ta(skip_long_w_ta)) # Should pass


    @patch('amane_cut.Balloons.detect_balloon') # Mock the complex floodFill part
    @patch('sklearn.cluster.KMeans')
    def test_define_balloon_flow(self, mock_kmeans, mock_detect_balloon_method):
        # Mocking an image for Balloons instance
        with patch('cv2.imread', return_value=create_mock_image_data(1000, 800)):
            balloons_instance = Balloons("dummy_path.png")
        balloons_instance.img_height = 1000 # Manually set for is_good_ta
        balloons_instance.img_width = 800

        # Sample TextAnnotations
        ta_raw_1 = {"description": "良い言葉", "boundingPoly": {"vertices": [{"x":10,"y":10},{"x":60,"y":10},{"x":60,"y":30},{"x":10,"y":30}]}} # rect [10,10,50,20]
        ta_raw_2 = {"description": "これも良い", "boundingPoly": {"vertices": [{"x":15,"y":15},{"x":65,"y":15},{"x":65,"y":35},{"x":15,"y":35}]}} # rect [15,15,50,20], overlaps with 1
        ta_raw_3 = {"description": "別の場所", "boundingPoly": {"vertices": [{"x":100,"y":100},{"x":150,"y":100},{"x":150,"y":120},{"x":100,"y":120}]}} # rect [100,100,50,20]
        ta_raw_ng = {"description": "NG", "boundingPoly": {"vertices": [{"x":200,"y":200},{"x":210,"y":200},{"x":210,"y":205},{"x":200,"y":205}]}} # rect [200,200,10,5], likely bad geom

        text_annotations_input = [{}, ta_raw_1, ta_raw_2, ta_raw_3, ta_raw_ng] # OCR typically has empty first item

        # Mock is_good_ta to control filtering
        # Let ta_raw_1, ta_raw_2, ta_raw_3 pass, but ta_raw_ng fail
        def mock_is_good_ta_side_effect(ta_dict):
            # Crude check based on description for this test
            if ta_dict["description"] == "NG":
                return False
            return True
        balloons_instance.is_good_ta = MagicMock(side_effect=mock_is_good_ta_side_effect)
        
        # Mock _detect_laped: assume ta_raw_2 is a duplicate of ta_raw_1 to be removed
        # (combi[0] is ta_raw_1_val, combi[1] is ta_raw_2_val) -> remove combi[1] (ta_raw_2_val)
        # (combi[0] is ta_raw_1_val, combi[1] is ta_raw_3_val) -> no overlap
        # (combi[0] is ta_raw_2_val, combi[1] is ta_raw_3_val) -> no overlap (if ta_raw_2_val was not removed)

        # Let's simplify: ta_list becomes [ta_val_1, ta_val_3] after dup removal
        # ta_val_1 = {'rect': [10,10,50,20], 'text': '良い言葉'}
        # ta_val_3 = {'rect': [100,100,50,20], 'text': '別の場所'}
        
        # Mock detect_balloon to set ta_rect_list
        # These rects would be the output of floodFill based on ta_val_1 and ta_val_3
        mock_balloon_rect1 = (10, 10, 55, 25) # Slightly larger than ta_val_1's rect
        mock_balloon_rect2 = (100, 100, 55, 25) # Slightly larger than ta_val_3's rect
        mock_detect_balloon_method.side_effect = lambda: setattr(balloons_instance, 'ta_rect_list', [mock_balloon_rect1, mock_balloon_rect2])

        # Mock KMeans for tall balloon splitting (not triggered in this specific setup unless rects are tall)
        mock_kmeans_instance = MagicMock()
        mock_kmeans_instance.predict.return_value = np.array([0, 1]) # Dummy classes
        mock_kmeans.return_value = mock_kmeans_instance

        balloons_instance.define_balloon(text_annotations_input)

        # Assertions
        # is_good_ta calls: ta_raw_1, ta_raw_2, ta_raw_3, ta_raw_ng (4 calls)
        self.assertEqual(balloons_instance.is_good_ta.call_count, 4) 
        
        # After filtering and duplicate removal (assuming ta_raw_2 removed as dup of ta_raw_1)
        # self.ta_list should contain processed versions of ta_raw_1 and ta_raw_3
        # Note: The duplicate removal logic in original code is complex and might need more specific mocking of _detect_laped
        # For this test, we assume ta_raw_2 is removed because it overlaps and let's say len(ta_raw_1_text) >= len(ta_raw_2_text)
        
        self.assertEqual(len(balloons_instance.ta_list), 2) # ta_raw_1 and ta_raw_3 remain
        self.assertEqual(balloons_instance.ta_list[0]["text"], "良い言葉")
        self.assertEqual(balloons_instance.ta_list[1]["text"], "別の場所")

        mock_detect_balloon_method.assert_called_once()
        
        # Check ta_rect_dict (mapping balloon_rect to list of TAs inside it)
        self.assertIn(mock_balloon_rect1, balloons_instance.ta_rect_dict)
        self.assertEqual(len(balloons_instance.ta_rect_dict[mock_balloon_rect1]), 1)
        self.assertEqual(balloons_instance.ta_rect_dict[mock_balloon_rect1][0]["text"], "良い言葉")
        
        self.assertIn(mock_balloon_rect2, balloons_instance.ta_rect_dict)
        self.assertEqual(len(balloons_instance.ta_rect_dict[mock_balloon_rect2]), 1)
        self.assertEqual(balloons_instance.ta_rect_dict[mock_balloon_rect2][0]["text"], "別の場所")

        # Check final text_list (concatenated texts from balloons)
        self.assertIn("良い言葉", balloons_instance.text_list)
        self.assertIn("別の場所", balloons_instance.text_list)
        self.assertEqual(len(balloons_instance.text_list), 2)
        
        # KMeans should not be called if balloons are not excessively tall
        mock_kmeans.assert_not_called()


if __name__ == '__main__':
    unittest.main()
