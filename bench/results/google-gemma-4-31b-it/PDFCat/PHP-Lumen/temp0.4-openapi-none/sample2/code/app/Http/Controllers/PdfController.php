<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
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
        $outputFile = tempnam(sys_get_temp_dir(), 'concatenated_');
        $outputFile .= '.pdf';

        try {
            // 2. Store uploaded files temporarily
            foreach ($files as $file) {
                if ($file->getClientOriginalExtension() !== 'pdf') {
                    throw new \Exception("Only PDF files are allowed.");
                }
                
                $path = $file->store('temp_pdfs');
                $tempFiles[] = storage_path('app/' . $path);
            }

            // 3. Build the pdfunite command
            // pdfunite file1.pdf file2.pdf ... output.pdf
            $inputPaths = implode(' ', array_map('escapeshellarg', $tempFiles));
            $command = "pdfunite $inputPaths " . escapeshellarg($outputFile);
            
            exec($command, $output, $returnVar);

            if ($returnVar !== 0) {
                throw new \Exception("pdfunite failed to process the files.");
            }

            // 4. Return the concatenated PDF
            return new BinaryFileResponse($outputFile, 200, [
                'Content-Type' => 'application/pdf',
                'Content-Disposition' => 'attachment; filename="concatenated.pdf"'
            ]);

        } catch (\Exception $e) {
            return response()->json(['error' => 'An error occurred while processing the files: ' . $e->getMessage()], 500);
        } finally {
            // Cleanup temporary input files
            foreach ($tempFiles as $tempFile) {
                if (File::exists($tempFile)) {
                    File::delete($tempFile);
                }
            }
            // Note: We don't delete the $outputFile immediately because 
            // BinaryFileResponse needs it to stream the content. 
            // In a production environment, a scheduled cleanup task would be used.
        }
    }
}