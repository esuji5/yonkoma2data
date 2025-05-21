import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
import subprocess
import runpy

# Adjust sys.path to allow importing pdf_to_pages and utils from the src directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
# pdf_to_pages is imported dynamically by runpy, so no direct import needed here.
# import utils # utils is used by pdf_to_pages.py

class TestPdfToPages(unittest.TestCase):

    @patch('builtins.print')
    @patch('utils.check_argv_path')
    @patch('utils.get_path_list')
    @patch('utils.make_outdir')
    @patch('fitz.open')
    @patch('subprocess.run')
    def test_single_pdf_success(self, mock_subprocess_run, mock_fitz_open,
                                mock_make_outdir, mock_get_path_list,
                                mock_check_argv_path, mock_print):
        
        dummy_input_dir = 'dummy_pdf_dir'
        pdf_name = 'test.pdf' 
        full_pdf_path = os.path.join(dummy_input_dir, pdf_name)
        pdf_basename_no_ext = os.path.splitext(pdf_name)[0] # 'test'

        mock_check_argv_path.return_value = dummy_input_dir
        mock_get_path_list.return_value = [full_pdf_path]
        
        mock_pdf_doc = MagicMock()
        mock_pdf_doc.page_count = 2
        mock_fitz_open.return_value.__enter__.return_value = mock_pdf_doc # Handle context manager
        
        # Script logic: output_dir = utils.make_outdir(pdf_dir, os.path.splitext(os.path.basename(pdf_path))[0])
        # pdf_specific_output_folder_name is 'test'
        # make_outdir is called with parent_dir=dummy_input_dir, and new_folder_name=pdf_basename_no_ext
        # It returns the full path to the created directory.
        expected_output_dir_for_pdf = os.path.join(dummy_input_dir, pdf_basename_no_ext)
        mock_make_outdir.return_value = expected_output_dir_for_pdf
        
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Patch sys.argv for runpy
        with patch.object(sys, 'argv', ['pdf_to_pages.py', dummy_input_dir]):
            runpy.run_module('pdf_to_pages', run_name='__main__')

        mock_check_argv_path.assert_called_once_with(['pdf_to_pages.py', dummy_input_dir])
        mock_get_path_list.assert_called_once_with(dummy_input_dir, ext='.pdf')
        mock_fitz_open.assert_called_once_with(full_pdf_path)
        mock_make_outdir.assert_called_once_with(dummy_input_dir, pdf_basename_no_ext)

        expected_calls_subprocess = [
            call([
                'convert',
                '-density', '200',
                '-quality', '100',
                f'{full_pdf_path}[0]', # ImageMagick page indexing
                os.path.join(expected_output_dir_for_pdf, f'{pdf_basename_no_ext}_page_0001.png')
            ], check=True),
            call([
                'convert',
                '-density', '200',
                '-quality', '100',
                f'{full_pdf_path}[1]',
                os.path.join(expected_output_dir_for_pdf, f'{pdf_basename_no_ext}_page_0002.png')
            ], check=True)
        ]
        mock_subprocess_run.assert_has_calls(expected_calls_subprocess)
        self.assertEqual(mock_subprocess_run.call_count, 2)

    @patch('builtins.print')
    @patch('utils.check_argv_path')
    @patch('utils.get_path_list')
    @patch('utils.make_outdir')
    @patch('fitz.open')
    @patch('subprocess.run')
    def test_multiple_pdfs_success(self, mock_subprocess_run, mock_fitz_open,
                                   mock_make_outdir, mock_get_path_list,
                                   mock_check_argv_path, mock_print):
        dummy_input_dir = 'multi_pdf_dir'
        pdf_files = [
            os.path.join(dummy_input_dir, 'doc1.pdf'),
            os.path.join(dummy_input_dir, 'doc2.pdf')
        ]
        pdf_basenames_no_ext = ['doc1', 'doc2']

        mock_check_argv_path.return_value = dummy_input_dir
        mock_get_path_list.return_value = pdf_files
        
        # Mock fitz.open to return different page_counts for different PDFs
        mock_doc1 = MagicMock(); mock_doc1.page_count = 1
        mock_doc2 = MagicMock(); mock_doc2.page_count = 2
        mock_fitz_open.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_doc1)),
            MagicMock(__enter__=MagicMock(return_value=mock_doc2))
        ]

        # Mock make_outdir to return distinct output dirs for each PDF
        expected_output_dirs = [
            os.path.join(dummy_input_dir, pdf_basenames_no_ext[0]),
            os.path.join(dummy_input_dir, pdf_basenames_no_ext[1])
        ]
        mock_make_outdir.side_effect = expected_output_dirs
        
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        with patch.object(sys, 'argv', ['pdf_to_pages.py', dummy_input_dir]):
            runpy.run_module('pdf_to_pages', run_name='__main__')

        self.assertEqual(mock_fitz_open.call_count, 2)
        mock_fitz_open.assert_has_calls([call(pdf_files[0]), call(pdf_files[1])])

        self.assertEqual(mock_make_outdir.call_count, 2)
        mock_make_outdir.assert_has_calls([
            call(dummy_input_dir, pdf_basenames_no_ext[0]),
            call(dummy_input_dir, pdf_basenames_no_ext[1])
        ])

        expected_calls_subprocess = [
            call([
                'convert', '-density', '200', '-quality', '100',
                f'{pdf_files[0]}[0]',
                os.path.join(expected_output_dirs[0], f'{pdf_basenames_no_ext[0]}_page_0001.png')
            ], check=True),
            call([
                'convert', '-density', '200', '-quality', '100',
                f'{pdf_files[1]}[0]',
                os.path.join(expected_output_dirs[1], f'{pdf_basenames_no_ext[1]}_page_0001.png')
            ], check=True),
            call([
                'convert', '-density', '200', '-quality', '100',
                f'{pdf_files[1]}[1]',
                os.path.join(expected_output_dirs[1], f'{pdf_basenames_no_ext[1]}_page_0002.png')
            ], check=True),
        ]
        mock_subprocess_run.assert_has_calls(expected_calls_subprocess)
        self.assertEqual(mock_subprocess_run.call_count, 3) # 1 page for doc1, 2 pages for doc2

    @patch('builtins.print')
    @patch('utils.check_argv_path')
    @patch('utils.get_path_list')
    @patch('utils.make_outdir')
    @patch('fitz.open')
    @patch('subprocess.run')
    def test_subprocess_failure_non_zero_return(self, mock_subprocess_run, mock_fitz_open,
                                               mock_make_outdir, mock_get_path_list,
                                               mock_check_argv_path, mock_print):
        dummy_input_dir = 'dummy_pdf_dir'
        pdf_name = 'fail.pdf'
        full_pdf_path = os.path.join(dummy_input_dir, pdf_name)
        pdf_basename_no_ext = 'fail'

        mock_check_argv_path.return_value = dummy_input_dir
        mock_get_path_list.return_value = [full_pdf_path]
        mock_pdf_doc = MagicMock(); mock_pdf_doc.page_count = 1
        mock_fitz_open.return_value.__enter__.return_value = mock_pdf_doc
        expected_output_dir_for_pdf = os.path.join(dummy_input_dir, pdf_basename_no_ext)
        mock_make_outdir.return_value = expected_output_dir_for_pdf
        
        mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="Conversion failed")

        with patch.object(sys, 'argv', ['pdf_to_pages.py', dummy_input_dir]):
            runpy.run_module('pdf_to_pages', run_name='__main__')
        
        mock_print.assert_any_call(f"Failed to convert page 1 of {full_pdf_path}. Error: Conversion failed")

    @patch('builtins.print')
    @patch('utils.check_argv_path')
    @patch('utils.get_path_list')
    @patch('utils.make_outdir')
    @patch('fitz.open')
    @patch('subprocess.run')
    def test_subprocess_failure_exception(self, mock_subprocess_run, mock_fitz_open,
                                          mock_make_outdir, mock_get_path_list,
                                          mock_check_argv_path, mock_print):
        dummy_input_dir = 'dummy_pdf_dir'
        pdf_name = 'exception.pdf'
        full_pdf_path = os.path.join(dummy_input_dir, pdf_name)
        pdf_basename_no_ext = 'exception'

        mock_check_argv_path.return_value = dummy_input_dir
        mock_get_path_list.return_value = [full_pdf_path]
        mock_pdf_doc = MagicMock(); mock_pdf_doc.page_count = 1
        mock_fitz_open.return_value.__enter__.return_value = mock_pdf_doc
        expected_output_dir_for_pdf = os.path.join(dummy_input_dir, pdf_basename_no_ext)
        mock_make_outdir.return_value = expected_output_dir_for_pdf
        
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=['convert'], stderr="Fatal error"
        )

        with patch.object(sys, 'argv', ['pdf_to_pages.py', dummy_input_dir]):
            runpy.run_module('pdf_to_pages', run_name='__main__')
        
        mock_print.assert_any_call(f"Failed to convert page 1 of {full_pdf_path}. Error: Command '['convert', '-density', '200', '-quality', '100', '{full_pdf_path}[0]', '{os.path.join(expected_output_dir_for_pdf, f'{pdf_basename_no_ext}_page_0001.png')}']' returned non-zero exit status 1.")


    @patch('builtins.print')
    @patch('utils.check_argv_path')
    @patch('utils.get_path_list')
    @patch('utils.make_outdir')
    @patch('fitz.open')
    @patch('subprocess.run')
    def test_pdf_with_zero_pages(self, mock_subprocess_run, mock_fitz_open,
                                 mock_make_outdir, mock_get_path_list,
                                 mock_check_argv_path, mock_print):
        dummy_input_dir = 'dummy_pdf_dir'
        pdf_name = 'zero_page.pdf'
        full_pdf_path = os.path.join(dummy_input_dir, pdf_name)
        pdf_basename_no_ext = 'zero_page'

        mock_check_argv_path.return_value = dummy_input_dir
        mock_get_path_list.return_value = [full_pdf_path]
        
        mock_pdf_doc = MagicMock()
        mock_pdf_doc.page_count = 0 # Zero pages
        mock_fitz_open.return_value.__enter__.return_value = mock_pdf_doc
        
        expected_output_dir_for_pdf = os.path.join(dummy_input_dir, pdf_basename_no_ext)
        mock_make_outdir.return_value = expected_output_dir_for_pdf

        with patch.object(sys, 'argv', ['pdf_to_pages.py', dummy_input_dir]):
            runpy.run_module('pdf_to_pages', run_name='__main__')

        mock_fitz_open.assert_called_once_with(full_pdf_path)
        mock_make_outdir.assert_called_once_with(dummy_input_dir, pdf_basename_no_ext)
        mock_subprocess_run.assert_not_called() # subprocess.run should not be called for zero pages
        mock_print.assert_any_call(f"PDF {full_pdf_path} has 0 pages. Skipping.")


if __name__ == '__main__':
    unittest.main()
