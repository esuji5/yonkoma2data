import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import os
import sys
import pickle
import csv
from pathlib import Path
import runpy

# Adjust sys.path to allow importing modules from the src directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
# pickle_to_serif_data.py will be run by runpy

# Mock the Balloon class from extract_serif.balloon
# This is crucial as pickle_to_serif_data.py uses it.
mock_balloon_module = MagicMock()
MockBalloonClass = MagicMock()
mock_balloon_module.Balloon = MockBalloonClass
sys.modules['extract_serif.balloon'] = mock_balloon_module


class TestPickleToSerifData(unittest.TestCase):

    def setUp(self):
        # Reset mocks before each test
        MockBalloonClass.reset_mock()

        # Common mock data
        self.dummy_pickle_path_str = "dummy_pickles/data.pickle"
        self.dummy_pickle_path = Path(self.dummy_pickle_path_str)
        
        # Expected CSV output directory based on script logic: (pickle_path / ".." / "..").resolve() / "csv"
        # Assuming pickle_path is "dummy_pickles/data.pickle", ".." is "dummy_pickles", "../.." is "." (current dir for test)
        # So csv_dir becomes "./csv"
        self.expected_csv_dir = Path(".") / "csv"
        self.expected_csv_filename = f"{self.dummy_pickle_path.name}.csv" # data.pickle.csv - script uses .name
        self.expected_csv_filepath = self.expected_csv_dir / self.expected_csv_filename


    @patch('utils.check_argv_path')
    @patch('utils.pickle_load')
    @patch('utils.make_outdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('csv.DictWriter')
    @patch('builtins.print') # To suppress print statements from the script
    def test_successful_conversion(self, mock_print, mock_csv_dict_writer, mock_builtin_open,
                                   mock_make_outdir, mock_pickle_load, mock_check_argv_path):
        
        mock_check_argv_path.return_value = self.dummy_pickle_path_str
        mock_make_outdir.return_value = self.expected_csv_dir

        # Mock data from pickle_load
        mock_ocr_data_values = [
            {"image_path": "img/001.jpg", "text_annotation": ["anno1_img1", "anno2_img1"]},
            {"image_path": "img/002.jpg", "text_annotation": ["anno1_img2"]},
        ]
        mock_pickle_load.return_value = {"values": mock_ocr_data_values}

        # Mock Balloon instances and their make_serif method
        mock_balloon_instance1 = MagicMock()
        mock_balloon_instance1.make_serif.return_value = "Serif for image 1"
        mock_balloon_instance1.highlight_texts.return_value = MagicMock() # Simulate PIL Image

        mock_balloon_instance2 = MagicMock()
        mock_balloon_instance2.make_serif.return_value = "Serif for image 2"
        mock_balloon_instance2.highlight_texts.return_value = MagicMock()

        MockBalloonClass.side_effect = [mock_balloon_instance1, mock_balloon_instance2]
        
        # Mock CSV writer
        mock_csv_writer_instance = MagicMock()
        mock_csv_dict_writer.return_value = mock_csv_writer_instance

        with patch.object(sys, 'argv', ['pickle_to_serif_data.py', self.dummy_pickle_path_str]):
            runpy.run_module('pickle_to_serif_data', run_name='__main__')

        mock_check_argv_path.assert_called_once_with(['pickle_to_serif_data.py', self.dummy_pickle_path_str])
        mock_pickle_load.assert_called_once_with(self.dummy_pickle_path)
        
        # make_outdir is called with resolved path: (Path("dummy_pickles/data.pickle") / ".." / "..").resolve()
        # which is Path(".").resolve() in this test setup if dummy_pickles is at root.
        # Let's ensure make_outdir is called with the correct logic.
        # The script does: csv_dir = utils.make_outdir((pickle_path / ".." / "..").resolve(), "csv")
        # If pickle_path is Path("dummy_pickles/data.pickle"), then pickle_path / ".." is Path("dummy_pickles")
        # then pickle_path / ".." / ".." is Path(".")
        # So it calls make_outdir(Path(".").resolve(), "csv")
        mock_make_outdir.assert_called_once_with(Path(".").resolve(), "csv")

        mock_builtin_open.assert_called_once_with(self.expected_csv_filepath, "w")
        
        MockBalloonClass.assert_has_calls([
            call(mock_ocr_data_values[0]["image_path"], mock_ocr_data_values[0]["text_annotation"]),
            call(mock_ocr_data_values[1]["image_path"], mock_ocr_data_values[1]["text_annotation"]),
        ])
        mock_balloon_instance1.make_serif.assert_called_once()
        mock_balloon_instance2.make_serif.assert_called_once()

        mock_csv_dict_writer.assert_called_once_with(ANY, fieldnames=["img_path", "serif"])
        mock_csv_writer_instance.writeheader.assert_called_once()
        expected_csv_rows = [
            {"img_path": "img/001.jpg", "serif": "Serif for image 1"},
            {"img_path": "img/002.jpg", "serif": "Serif for image 2"},
        ]
        # Check each call to writerow
        calls = [call(row) for row in expected_csv_rows]
        mock_csv_writer_instance.writerow.assert_has_calls(calls)
        self.assertEqual(mock_csv_writer_instance.writerow.call_count, 2)


    @patch('utils.check_argv_path')
    @patch('utils.pickle_load')
    @patch('utils.make_outdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('csv.DictWriter')
    @patch('builtins.print')
    def test_empty_ocr_data(self, mock_print, mock_csv_dict_writer, mock_builtin_open,
                            mock_make_outdir, mock_pickle_load, mock_check_argv_path):
        mock_check_argv_path.return_value = self.dummy_pickle_path_str
        mock_make_outdir.return_value = self.expected_csv_dir
        mock_pickle_load.return_value = {"values": []} # Empty data

        mock_csv_writer_instance = MagicMock()
        mock_csv_dict_writer.return_value = mock_csv_writer_instance

        with patch.object(sys, 'argv', ['pickle_to_serif_data.py', self.dummy_pickle_path_str]):
            runpy.run_module('pickle_to_serif_data', run_name='__main__')

        mock_builtin_open.assert_called_once_with(self.expected_csv_filepath, "w")
        mock_csv_writer_instance.writeheader.assert_called_once()
        mock_csv_writer_instance.writerow.assert_not_called() # No data rows
        MockBalloonClass.assert_not_called() # Balloon should not be instantiated if values are empty

    @patch('utils.check_argv_path')
    @patch('utils.pickle_load')
    @patch('builtins.print')
    def test_pickle_file_not_found(self, mock_print, mock_pickle_load, mock_check_argv_path):
        mock_check_argv_path.return_value = "non_existent.pickle"
        mock_pickle_load.side_effect = FileNotFoundError("Pickle file not found")

        with patch.object(sys, 'argv', ['pickle_to_serif_data.py', "non_existent.pickle"]):
            with self.assertRaises(FileNotFoundError): # Error should propagate
                runpy.run_module('pickle_to_serif_data', run_name='__main__')
        mock_print.assert_not_called() # Script doesn't catch this explicitly

    @patch('utils.check_argv_path')
    @patch('utils.pickle_load')
    @patch('builtins.print')
    def test_corrupt_pickle_file(self, mock_print, mock_pickle_load, mock_check_argv_path):
        mock_check_argv_path.return_value = self.dummy_pickle_path_str
        mock_pickle_load.side_effect = pickle.UnpicklingError("Corrupt pickle")

        with patch.object(sys, 'argv', ['pickle_to_serif_data.py', self.dummy_pickle_path_str]):
            with self.assertRaises(pickle.UnpicklingError):
                runpy.run_module('pickle_to_serif_data', run_name='__main__')
        mock_print.assert_not_called()

    @patch('utils.check_argv_path')
    @patch('utils.pickle_load')
    @patch('utils.make_outdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('csv.DictWriter')
    @patch('builtins.print')
    def test_csv_writing_error(self, mock_print, mock_csv_dict_writer, mock_builtin_open,
                               mock_make_outdir, mock_pickle_load, mock_check_argv_path):
        mock_check_argv_path.return_value = self.dummy_pickle_path_str
        mock_make_outdir.return_value = self.expected_csv_dir
        mock_ocr_data_values = [{"image_path": "img/001.jpg", "text_annotation": ["anno1"]}]
        mock_pickle_load.return_value = {"values": mock_ocr_data_values}

        mock_balloon_instance = MagicMock()
        mock_balloon_instance.make_serif.return_value = "Serif text"
        mock_balloon_instance.highlight_texts.return_value = MagicMock()
        MockBalloonClass.return_value = mock_balloon_instance
        
        # Simulate error during CSV writing
        mock_csv_writer_instance = MagicMock()
        mock_csv_writer_instance.writeheader.side_effect = IOError("CSV write error")
        mock_csv_dict_writer.return_value = mock_csv_writer_instance
        
        with patch.object(sys, 'argv', ['pickle_to_serif_data.py', self.dummy_pickle_path_str]):
            with self.assertRaises(IOError): # Expecting the IOError from writeheader to propagate
                runpy.run_module('pickle_to_serif_data', run_name='__main__')
        
        mock_builtin_open.assert_called_once_with(self.expected_csv_filepath, "w")
        mock_csv_writer_instance.writeheader.assert_called_once()
        mock_csv_writer_instance.writerow.assert_not_called() # Should fail before writing rows


if __name__ == '__main__':
    unittest.main()
