<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class PdfController extends Controller
{
    public function concatenate(Request $request)
    {
        // 1. Validation: Check if 'files' array exists and is not empty
        if (!$request->hasFile('files') || !is_array($request->file('files'))) {
            return response()->json(['error' => 'Invalid input or missing files.'], 400);
        }

        $files = $request->file('files');
        if (empty($files)) {
            return response()->json(['error' => 'Invalid input or missing files.'], 400);
        }

        $tempFiles = [];
        $outputFile = tempnam(sys_get_temp_dir(), 'concatenated_') . '.pdf';

        try {
            // 2. Store uploaded files temporarily
            foreach ($files as $file) {
                if ($file->isValid() && $file->getClientMimeType() === 'application/pdf') {
                    $path = $file->store('temp_pdfs'); 
                    // In Lumen, store() puts files in storage/app/temp_pdfs
                    $fullPath = storage_path('app/' . $path);
                    $tempFiles[] = $fullPath;
                }
            }

            if (count($tempFiles) < 2) {
                // Technically pdfunite needs at least 2 files to "concatenate", 
                // but if only 1 valid PDF is provided, we can just return that one.
                if (count($tempFiles) === 1) {
                    return response()->file($tempFiles[0], 'application/pdf');
                }
                return response()->json(['error' => 'At least one valid PDF file is required.'], 400);
            }

            // 3. Build the pdfunite command
            // pdfunite file1.pdf file2.pdf ... output.pdf
            $inputFilesList = implode(' ', array_map('escapeshellarg', $tempFiles));
            $command = "pdfunite $inputFilesList " . escapeshellarg($outputFile);
            
            exec($command, $output, $returnVar);

            if ($returnVar !== 0) {
                throw new \Exception("pdfunite failed to process files.");
            }

            // 4. Return the resulting PDF
            return response()->file($outputFile, 'application/pdf', true);

        } catch (\Exception $e) {
            return response()->json(['error' => 'An error occurred while processing the files.'], 500);
        } finally {
            // Cleanup temporary input files
            foreach ($tempFiles as $f) {
                if (file_exists($f)) @unlink($f);
            }
            // Note: The output file is handled by the response or cleaned up by OS temp dir
        }
    }
}