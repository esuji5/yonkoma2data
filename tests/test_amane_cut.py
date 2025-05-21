import unittest
from unittest.mock import patch, MagicMock, call, ANY
import numpy as np
import cv2 # Only for type hinting if necessary, actual cv2 calls should be mocked
import os
import sys

# Adjust path to import amane_cut and its utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import amane_cut
import utils # amane_cut uses utils
import pdf_to_file.cut_by_paint_out as cut_po # amane_cut uses this

# Helper to create a mock image (numpy array)
def create_mock_image(height, width, channels=3, dtype=np.uint8, fill_value=0):
    # Create an image with a specific fill value
    if channels == 1:
        shape = (height, width)
    else:
        shape = (height, width, channels)
    img = np.full(shape, fill_value, dtype=dtype)
    return img

class TestAmaneCut(unittest.TestCase):

    def setUp(self):
        # Basic args for amane_cut, reset for each test
        self.mock_args = MagicMock()
        self.mock_args.filepath = 'dummy_input_dir'
        self.mock_args.pagetype = 'normal' 
        self.mock_args.with_subtitle = False
        self.mock_args.shave_subtitle = False
        self.mock_args.only_koma = False
        self.mock_args.start = 0
        self.mock_args.end = 0
        self.mock_args.tobirae = False
        self.mock_args.pad_x = 50 
        self.mock_args.pad_y = 27
        self.mock_args.ext = 'jpg'
        
        amane_cut.args = self.mock_args
        amane_cut.padding_x = self.mock_args.pad_x
        amane_cut.padding_y = self.mock_args.pad_y
        
        amane_cut.good_cons_num_y = 4 
        if self.mock_args.with_subtitle or self.mock_args.shave_subtitle:
            amane_cut.good_cons_num_y +=1
            
        amane_cut.odd_cp_list = []
        amane_cut.even_cp_list = []
        amane_cut.not_cut_img_path_dict = {}
        amane_cut.even_page_cp = ([],[]) 
        amane_cut.odd_page_cp = ([],[])


    @patch('cv2.imwrite')
    def test_cut_koma_simple_case(self, mock_cv_imwrite):
        mock_img_data = create_mock_image(200, 200, channels=3)
        contour_data = np.array([10, 20, 50, 60, 3000]) # x, y, w, h, size
        
        amane_cut.padding_x = 10 
        amane_cut.padding_y = 5
        
        koma_img_padding = amane_cut.cut_koma(contour_data, mock_img_data, padding=True)
        self.assertEqual(koma_img_padding.shape, (70, 70, 3))

        koma_img_no_padding = amane_cut.cut_koma(contour_data, mock_img_data, padding=False)
        self.assertEqual(koma_img_no_padding.shape, (60, 50, 3))
        
        amane_cut.imwrite("test_path", "01", koma_img_padding, sufix="_test", ext="png")
        mock_cv_imwrite.assert_called_with("test_path-01_test.png", koma_img_padding)

    @patch('cv2.imwrite')
    def test_imwrite_empty_image(self, mock_cv_imwrite):
        empty_image = np.array([])
        amane_cut.imwrite("test_path", "02", empty_image, sufix="_empty")
        mock_cv_imwrite.assert_not_called()

        amane_cut.imwrite("test_path", "03", None, sufix="_none")
        mock_cv_imwrite.assert_not_called()

    def test_find_average_point(self):
        con1_l = np.array([[10, 20, 30, 40, 1200]]*4, dtype=np.int32)
        con1_r = np.array([[110, 20, 30, 40, 1200]]*4, dtype=np.int32)
        con2_l = np.array([[15, 25, 35, 45, 1500]]*4, dtype=np.int32)
        con2_r = np.array([[115, 25, 35, 45, 1500]]*4, dtype=np.int32)

        cp_list_normal = [(con1_l, con1_r), (con2_l, con2_r)]
        
        amane_cut.args.pagetype = 'normal'
        mean_l, mean_r = amane_cut.find_average_point(cp_list_normal)
        expected_mean_l = np.mean(np.array([con1_l, con2_l]), axis=0).astype(int)
        expected_mean_r = np.mean(np.array([con1_r, con2_r]), axis=0).astype(int)
        np.testing.assert_array_equal(mean_l, expected_mean_l)
        np.testing.assert_array_equal(mean_r, expected_mean_r)

        cp_list_wide = [(con1_l, np.array([],dtype=np.int32).reshape(0,5)), (con2_l, np.array([],dtype=np.int32).reshape(0,5))]
        amane_cut.args.pagetype = 'wide'
        mean_l_wide, mean_r_wide = amane_cut.find_average_point(cp_list_wide)
        expected_mean_l_wide = np.mean(np.array([con1_l, con2_l]), axis=0).astype(int)
        np.testing.assert_array_equal(mean_l_wide, expected_mean_l_wide)
        self.assertEqual(mean_r_wide.size, 0)

    @patch('cv2.connectedComponentsWithStats')
    @patch('pdf_to_file.cut_by_paint_out.make_paint_out_img')
    @patch('pdf_to_file.cut_by_paint_out.get_canny')
    def test_make_labeled_contours(self, mock_get_canny, mock_make_paint_out_img, mock_connected_components):
        mock_img_data = create_mock_image(100,100, channels=1)
        mock_canny_output1 = create_mock_image(100,100, channels=1, fill_value=10)
        mock_canny_output2 = create_mock_image(100,100, channels=1, fill_value=20) 
        mock_paint_out_output = create_mock_image(100,100, channels=1, fill_value=30)
        mock_stats = np.array([[0,0,10,10,100], [10,10,20,20,400]], dtype=np.int32)
        mock_connected_components.return_value = (2, MagicMock(), mock_stats, MagicMock())

        # Scenario 1: make_paint_out_img returns an image
        mock_get_canny.side_effect = [mock_canny_output1, mock_canny_output2]
        mock_make_paint_out_img.return_value = mock_paint_out_output
        
        contours = amane_cut.make_labeled_contours(mock_img_data, kind="1st")
        mock_get_canny.assert_has_calls([call(mock_img_data), call(mock_paint_out_output)])
        mock_make_paint_out_img.assert_called_once_with(mock_img_data, mock_canny_output1)
        mock_connected_components.assert_called_once_with(mock_canny_output2) 
        np.testing.assert_array_equal(contours, mock_stats)

        mock_get_canny.reset_mock(side_effect=True); mock_make_paint_out_img.reset_mock(); mock_connected_components.reset_mock()
        mock_connected_components.return_value = (2, MagicMock(), mock_stats, MagicMock())

        # Scenario 2: make_paint_out_img returns None, kind="1st"
        mock_make_paint_out_img.return_value = None
        mock_get_canny.return_value = mock_canny_output1
        
        contours_no_paintout_kind1 = amane_cut.make_labeled_contours(mock_img_data, kind="1st")
        mock_get_canny.assert_called_once_with(mock_img_data)
        mock_make_paint_out_img.assert_called_once_with(mock_img_data, mock_canny_output1)
        mock_connected_components.assert_not_called() 
        self.assertIsNone(contours_no_paintout_kind1)

        mock_get_canny.reset_mock(); mock_make_paint_out_img.reset_mock(); mock_connected_components.reset_mock()
        mock_connected_components.return_value = (2, MagicMock(), mock_stats, MagicMock()) 

        # Scenario 3: make_paint_out_img returns None, kind="2nd"
        mock_make_paint_out_img.return_value = None
        mock_get_canny.return_value = mock_canny_output1 
        
        contours_no_paintout_kind2 = amane_cut.make_labeled_contours(mock_img_data, kind="2nd")
        mock_get_canny.assert_called_once_with(mock_img_data)
        mock_make_paint_out_img.assert_called_once_with(mock_img_data, mock_canny_output1)
        mock_connected_components.assert_called_once_with(mock_canny_output1) 
        np.testing.assert_array_equal(contours_no_paintout_kind2, mock_stats)

    @patch('amane_cut.exec_po_2nd') 
    @patch('amane_cut.make_labeled_contours') 
    @patch('cv2.imread') 
    @patch('cv2.imwrite') 
    def test_exec_paint_out_cut_kind_2nd(self, mock_cv_imwrite, mock_imread, 
                                       mock_make_labeled_contours_func, mock_exec_po_2nd_func):
        dummy_img_path_list = ["dummy_path1.jpg", "dummy_path2.jpg"]
        mock_img_data_local = create_mock_image(100, 100) 
        mock_imread.return_value = mock_img_data_local
        mock_contours_stats = np.array([[0,0,10,10,100], [10,10,80,80,6400]], dtype=np.int32) 
        mock_make_labeled_contours_func.return_value = mock_contours_stats
        mock_shaved_img_output = create_mock_image(80, 80)
        mock_exec_po_2nd_func.return_value = mock_shaved_img_output

        with patch('amane_cut.output_shaved_path', 'mock_output_dir'):
            amane_cut.exec_paint_out_cut(dummy_img_path_list, kind="2nd")

        mock_imread.assert_has_calls([call("dummy_path1.jpg"), call("dummy_path2.jpg")])
        mock_make_labeled_contours_func.assert_has_calls([
            call(mock_img_data_local, "2nd"), call(mock_img_data_local, "2nd")])
        mock_exec_po_2nd_func.assert_has_calls([
             call(mock_contours_stats, mock_img_data_local, []), 
             call(mock_contours_stats, mock_img_data_local, [])])
        mock_cv_imwrite.assert_has_calls([
            call('mock_output_dir/dummy_path1-shaved.jpg', mock_shaved_img_output),
            call('mock_output_dir/dummy_path2-shaved.jpg', mock_shaved_img_output)
        ], any_order=False)

    @patch('utils.get_path_list') 
    @patch('cv2.imread')
    @patch('amane_cut.make_labeled_contours')
    @patch('pdf_to_file.cut_by_paint_out.parse_contours') 
    @patch('amane_cut.imwrite') 
    @patch('amane_cut.find_average_point') 
    def test_exec_paint_out_cut_kind_1st_normal_page(self, mock_find_avg_pt, mock_amane_imwrite, 
                                                 mock_parse_contours_func, mock_make_labeled_contours_func, 
                                                 mock_imread_func, mock_get_path_list_func):
        mock_get_path_list_func.return_value = ['page1.jpg']
        mock_img_data_local = create_mock_image(1000, 800) # H, W
        mock_imread_func.return_value = mock_img_data_local
        mock_initial_contours = np.array([[0,0,800,1000,800000]], dtype=np.int32)
        mock_make_labeled_contours_func.return_value = mock_initial_contours
        left_koma_data = [np.array([50,50+i*220,300,200,60000], dtype=np.int32) for i in range(4)]
        right_koma_data = [np.array([400,50+i*220,300,200,60000], dtype=np.int32) for i in range(4)]
        mock_parse_contours_func.return_value = (left_koma_data, right_koma_data, np.array([], dtype=np.int32).reshape(0,5))

        self.mock_args.pagetype = 'normal'
        amane_cut.args = self.mock_args
        amane_cut.good_cons_num_y = 4

        with patch('amane_cut.output_shaved_path', 'mock_output'), \
             patch('amane_cut.even_cp_list', []) as mock_even_list, \
             patch('amane_cut.not_cut_img_path_dict', {}) as mock_not_cut_dict:
            amane_cut.exec_paint_out_cut(['page1.jpg'], kind="1st")

        mock_parse_contours_func.assert_called_once_with(
            mock_initial_contours, 800, 1000, 4, 0.3, False, False, False)
        self.assertEqual(mock_amane_imwrite.call_count, 8)
        self.assertEqual(len(mock_even_list), 1)
        self.assertEqual(len(mock_not_cut_dict), 0)

    @patch('utils.get_path_list')
    @patch('cv2.imread')
    @patch('amane_cut.make_labeled_contours')
    @patch('pdf_to_file.cut_by_paint_out.parse_contours')
    @patch('amane_cut.imwrite')
    def test_exec_paint_out_cut_kind_1st_tobirae(self, mock_amane_imwrite, mock_parse_contours_func, mock_make_labeled_contours_func, mock_imread_func, mock_get_path_list_func):
        mock_get_path_list_func.return_value = ['page_tobirae.jpg']
        mock_img_data_local = create_mock_image(1000, 800)
        mock_imread_func.return_value = mock_img_data_local
        mock_initial_contours = np.array([[0,0,800,1000,800000]], dtype=np.int32)
        mock_make_labeled_contours_func.return_value = mock_initial_contours
        
        tobirae_contour = np.array([10,10,780,980,700000], dtype=np.int32)
        mock_parse_contours_func.return_value = ([], [], np.array([tobirae_contour]))

        self.mock_args.tobirae = True
        amane_cut.args = self.mock_args
        
        with patch('amane_cut.output_shaved_path', 'mock_output'), \
             patch('amane_cut.output_tobirae_path', 'mock_tobirae_output'), \
             patch('amane_cut.not_cut_img_path_dict', {}) as mock_not_cut_dict:
            amane_cut.exec_paint_out_cut(['page_tobirae.jpg'], kind="1st")

        mock_parse_contours_func.assert_called_once_with(
            mock_initial_contours, 800, 1000, 4, 0.3, False, False, True) 
        mock_amane_imwrite.assert_called_once_with('mock_tobirae_output/page_tobirae', 0, ANY, False, is_tobirae=True)
        self.assertEqual(len(mock_not_cut_dict), 0)

    @patch('utils.get_path_list')
    @patch('cv2.imread')
    @patch('amane_cut.make_labeled_contours')
    @patch('pdf_to_file.cut_by_paint_out.parse_contours')
    @patch('amane_cut.imwrite')
    def test_exec_paint_out_cut_kind_1st_subtitles(self, mock_amane_imwrite, mock_parse_contours_func, mock_make_labeled_contours_func, mock_imread_func, mock_get_path_list_func):
        mock_get_path_list_func.return_value = ['page_subtitle.jpg']
        mock_img_data_local = create_mock_image(1200, 800)
        mock_imread_func.return_value = mock_img_data_local
        mock_initial_contours = np.array([[0,0,800,1200,960000]], dtype=np.int32)
        mock_make_labeled_contours_func.return_value = mock_initial_contours

        left_koma_data = [np.array([50, 50 + i*220, 100, 100, 10000], dtype=np.int32) for i in range(5)]
        right_koma_data = [np.array([200, 50 + i*220, 100, 100, 10000], dtype=np.int32) for i in range(5)]
        mock_parse_contours_func.return_value = (left_koma_data, right_koma_data, np.array([], dtype=np.int32).reshape(0,5))

        self.mock_args.with_subtitle = True
        self.mock_args.shave_subtitle = True 
        amane_cut.args = self.mock_args
        amane_cut.good_cons_num_y = 5 

        with patch('amane_cut.output_shaved_path', 'mock_output'), \
             patch('amane_cut.even_cp_list', []) as mock_even_list:
            amane_cut.exec_paint_out_cut(['page_subtitle.jpg'], kind="1st")
        
        mock_parse_contours_func.assert_called_once_with(
            mock_initial_contours, 800, 1200, 5, 0.3, False, False, False) 
        self.assertEqual(mock_amane_imwrite.call_count, 8) 
        self.assertEqual(len(mock_even_list[0][0]), 4) 
        self.assertEqual(len(mock_even_list[0][1]), 4)

    @patch('utils.get_path_list')
    @patch('cv2.imread')
    @patch('amane_cut.make_labeled_contours')
    @patch('pdf_to_file.cut_by_paint_out.parse_contours')
    @patch('amane_cut.imwrite')
    def test_exec_paint_out_cut_kind_1st_pagetypes(self, mock_amane_imwrite, mock_parse_contours_func, mock_make_labeled_contours_func, mock_imread_func, mock_get_path_list_func):
        mock_get_path_list_func.return_value = ['page_wide.jpg']
        mock_img_data_local = create_mock_image(1000, 1600) # Wide image
        mock_imread_func.return_value = mock_img_data_local
        mock_initial_contours = np.array([[0,0,1600,1000,1600000]], dtype=np.int32)
        mock_make_labeled_contours_func.return_value = mock_initial_contours
        
        left_koma_data = [np.array([50,50+i*220,300,200,60000], dtype=np.int32)]*4
        mock_parse_contours_func.return_value = (left_koma_data, [], np.array([], dtype=np.int32).reshape(0,5))

        self.mock_args.pagetype = 'wide'
        amane_cut.args = self.mock_args
        amane_cut.good_cons_num_y = 4

        with patch('amane_cut.output_shaved_path', 'mock_output'), \
             patch('amane_cut.even_cp_list', []) as mock_even_list:
            amane_cut.exec_paint_out_cut(['page_wide.jpg'], kind="1st")
        
        mock_parse_contours_func.assert_called_once_with(
            mock_initial_contours, 1600, 1000, 4, 0.3, True, False, False) 
        self.assertEqual(mock_amane_imwrite.call_count, 4) 
        self.assertEqual(len(mock_even_list[0][0]), 4) 
        self.assertEqual(len(mock_even_list[0][1]), 0)

    @patch('utils.get_path_list')
    @patch('cv2.imread')
    @patch('amane_cut.make_labeled_contours')
    @patch('pdf_to_file.cut_by_paint_out.parse_contours')
    @patch('amane_cut.imwrite')
    def test_exec_paint_out_cut_kind_1st_bad_contours(self, mock_amane_imwrite, mock_parse_contours_func, mock_make_labeled_contours_func, mock_imread_func, mock_get_path_list_func):
        mock_get_path_list_func.return_value = ['page_bad.jpg']
        mock_img_data_local = create_mock_image(1000, 800)
        mock_imread_func.return_value = mock_img_data_local
        mock_initial_contours = np.array([[0,0,800,1000,800000]], dtype=np.int32)
        mock_make_labeled_contours_func.return_value = mock_initial_contours
        
        left_koma_data = [np.array([50,50,100,100,10000], dtype=np.int32)]*2 
        right_koma_data = [np.array([200,50,100,100,10000], dtype=np.int32)]*2
        mock_parse_contours_func.return_value = (left_koma_data, right_koma_data, np.array([], dtype=np.int32).reshape(0,5))

        amane_cut.args.pagetype = 'normal'
        amane_cut.good_cons_num_y = 4 

        with patch('amane_cut.output_shaved_path', 'mock_output'), \
             patch('amane_cut.not_cut_img_path_dict', {}) as mock_not_cut_dict:
            amane_cut.exec_paint_out_cut(['page_bad.jpg'], kind="1st")
        
        self.assertEqual(mock_amane_imwrite.call_count, 0) 
        self.assertIn(0, mock_not_cut_dict) 
        self.assertEqual(mock_not_cut_dict[0], 'page_bad.jpg')

    @patch('amane_cut.imwrite') 
    @patch('amane_cut.cut_koma')
    @patch('cv2.imread')
    @patch('cv2.cvtColor') 
    @patch('amane_cut.detect_only_koma')
    def test_fallback_average_cut_logic(self, mock_detect_only_koma, mock_cv_cvtColor_func, 
                                      mock_imread_func, mock_cut_koma_func, mock_amane_imwrite_func):
        
        mock_img_data_local = create_mock_image(1000, 800) 
        mock_imread_func.return_value = mock_img_data_local
        
        mock_gray_img = create_mock_image(1000, 800, channels=1); mock_gray_img.fill(128)
        mock_cv_cvtColor_func.return_value = mock_gray_img

        mock_koma_cut_output = create_mock_image(100,100)
        mock_cut_koma_func.side_effect = lambda con, img, pad: \
            mock_koma_cut_output if pad else img[con[1]:con[1]+con[3], con[0]:con[0]+con[2]]

        not_cut_paths_local = {0: 'page_even.jpg', 1: 'page_odd.jpg'}
        
        avg_left_con_data = [np.array([50,50+i*120,100,100,10000], dtype=np.int32) for i in range(4)]
        avg_right_con_data = [np.array([200,50+i*120,100,100,10000], dtype=np.int32) for i in range(4)]
        
        amane_cut.even_page_cp = (avg_left_con_data, avg_right_con_data)
        amane_cut.odd_page_cp = (avg_left_con_data, avg_right_con_data)
        
        self.mock_args.only_koma = False
        amane_cut.args = self.mock_args

        with patch('amane_cut.output_koma_path', 'mock_avg_koma_output'):
            # Simulate the loop from amane_cut.py's __main__ if not_cut_img_path_dict:
            for idx, img_path_val in not_cut_paths_local.items():
                img_read = cv2.imread(img_path_val) 
                if img_read is None: continue
                gray_img = cv2.cvtColor(img_read, cv2.COLOR_BGR2GRAY) 
                if gray_img.mean() >= 250: continue 
                img_o_copy = img_read.copy() 
                cut_base_path = os.path.join(amane_cut.output_koma_path, os.path.basename(img_path_val)[:-4])
                
                current_left_cons, current_right_cons = amane_cut.odd_page_cp if idx % 2 == 1 else amane_cut.even_page_cp
                
                if amane_cut.args.only_koma:
                    current_left_cons, current_right_cons = amane_cut.detect_only_koma(current_left_cons, current_right_cons, amane_cut.even_page_cp, amane_cut.odd_page_cp, gray_img)

                for i, con_val in enumerate(current_right_cons):
                    koma_img_res = amane_cut.cut_koma(con_val, img_o_copy, True)
                    amane_cut.imwrite(cut_base_path, i + 1, koma_img_res, "-pad")
                for i, con_val in enumerate(current_left_cons):
                    koma_img_res = amane_cut.cut_koma(con_val, img_o_copy, True)
                    amane_cut.imwrite(cut_base_path, i + 1 + len(current_right_cons), koma_img_res, "-pad")
        
        self.assertEqual(mock_amane_imwrite_func.call_count, 16)
        mock_detect_only_koma.assert_not_called() 
        self.assertEqual(mock_cv_cvtColor_func.call_count, len(not_cut_paths_local))

        # Test with only_koma = True
        mock_amane_imwrite_func.reset_mock(); mock_detect_only_koma.reset_mock()
        mock_cv_cvtColor_func.reset_mock(); mock_cut_koma_func.reset_mock()
        mock_cut_koma_func.side_effect = lambda con, img, pad: \
            mock_koma_cut_output if pad else img[con[1]:con[1]+con[3], con[0]:con[0]+con[2]]
        mock_detect_only_koma.return_value = (avg_left_con_data[:2], avg_right_con_data[:2])
        self.mock_args.only_koma = True
        amane_cut.args = self.mock_args

        with patch('amane_cut.output_koma_path', 'mock_avg_koma_output'):
            for idx, img_path_val in not_cut_paths_local.items():
                img_read = cv2.imread(img_path_val)
                gray_img = cv2.cvtColor(img_read, cv2.COLOR_BGR2GRAY)
                img_o_copy = img_read.copy()
                cut_base_path = os.path.join(amane_cut.output_koma_path, os.path.basename(img_path_val)[:-4])
                left_cons_orig, right_cons_orig = amane_cut.odd_page_cp if idx % 2 == 1 else amane_cut.even_page_cp
                current_left_cons, current_right_cons = amane_cut.detect_only_koma(left_cons_orig, right_cons_orig, amane_cut.even_page_cp, amane_cut.odd_page_cp, gray_img)
                for i, con_val in enumerate(current_right_cons):
                    koma_img_res = amane_cut.cut_koma(con_val, img_o_copy, True)
                    amane_cut.imwrite(cut_base_path, i + 1, koma_img_res, "-pad")
                for i, con_val in enumerate(current_left_cons):
                    koma_img_res = amane_cut.cut_koma(con_val, img_o_copy, True)
                    amane_cut.imwrite(cut_base_path, i + 1 + len(current_right_cons), koma_img_res, "-pad")
        
        self.assertEqual(mock_detect_only_koma.call_count, len(not_cut_paths_local))
        self.assertEqual(mock_amane_imwrite_func.call_count, 8) 
        self.assertEqual(mock_cv_cvtColor_func.call_count, len(not_cut_paths_local))

if __name__ == '__main__':
    unittest.main()
