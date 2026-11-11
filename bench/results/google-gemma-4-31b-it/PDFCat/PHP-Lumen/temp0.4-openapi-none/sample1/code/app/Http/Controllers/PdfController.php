<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class PdfController extends Controller
{
    public function concatenate(Request $request)
    {
        // Validate that 'files' array exists and is not empty
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
            // Store uploaded files temporarily
            foreach ($files as $file) {
                if ($file->getClientOriginalExtension() !== 'pdf') {
                    throw new \Exception("Only PDF files are allowed.");
                }
                
                $path = $file->store('temp_pdfs'); 
                // Since Lumen's store() uses the disk, we get the absolute path
                $fullPath = storage_path('app/' . $path);
                $tempFiles[] = $fullPath;
            }

            // Build the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
            $inputFilesList = implode(' ', array_map('escapeshellarg', $tempFiles));
            $command = "pdfunite $inputFilesList " . escapeshellarg($outputFile);
            
            exec($command, $output, $returnVar);

            if ($returnVar !== 0) {
                throw new \Exception("pdfunite failed to process files.");
            }

            // Return the file as a PDF response
            return response()->download($outputFile, 'concatenated.pdf', [
                'Content-Type' => 'application/pdf'
            ]);

        } catch (\Exception $e) {
            return response()->json(['error' => 'An error occurred while processing the files: ' . $e->getMessage()], 500);
        } finally {
            // Cleanup temporary input files
            foreach ($tempFiles as $tempFile) {
                if (file_exists($tempFile)) {
                    unlink($tempFile);
                }
            }
            // Note: In a production environment, we would use a queued job or 
            // a cleanup script to delete the $outputFile after the response is sent.
        }
    }
}