<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class PdfController extends Controller
{
    public function concatenate(Request $request)
    {
        // Validate that 'files' array exists and contains files
        if (!$request->hasFile('files') || !is_array($request->file('files'))) {
            return response()->json(['error' => 'Invalid input or missing files.'], 400);
        }

        $files = $request->file('files');
        if (empty($files)) {
            return response()->json(['error' => 'Invalid input or missing files.'], 400);
        }

        $tempPaths = [];
        $tempDir = storage_path('tmp');
        
        if (!is_dir($tempDir)) {
            mkdir($tempDir, 0777, true);
        }

        try {
            // Save uploaded files to temporary location
            foreach ($files as $index => $file) {
                if ($file->getClientMimeType() !== 'application/pdf') {
                    throw new \Exception("One or more uploaded files are not PDFs.");
                }
                
                $filename = "input_{$index}.pdf";
                $path = $tempDir . DIRECTORY_SEPARATOR . $filename;
                $file->move($tempDir, $filename);
                $tempPaths[] = $path;
            }

            $outputFile = $tempDir . DIRECTORY_SEPARATOR . 'concatenated_' . uniqid() . '.pdf';
            
            // Build the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
            $inputFilesList = implode(' ', array_map('escapeshellarg', $tempPaths));
            $command = "pdfunite {$inputFilesList} " . escapeshellarg($outputFile);
            
            exec($command, $output, $returnVar);

            if ($returnVar !== 0) {
                throw new \Exception("pdfunite failed to concatenate files.");
            }

            // Return the PDF file as a binary response
            return new BinaryFileResponse($outputFile, 200, [
                'Content-Type' => 'application/pdf',
                'Content-Disposition' => 'attachment; filename="concatenated.pdf"'
            ]);

        } catch (\Exception $e) {
            return response()->json(['error' => 'An error occurred while processing the files: ' . $e->getMessage()], 500);
        } finally {
            // Cleanup input files
            foreach ($tempPaths as $path) {
                if (file_exists($path)) {
                    unlink($path);
                }
            }
            // Note: In a production environment, you would use a scheduled task 
            // or a deferred response to clean up the output file after the download.
        }
    }
}