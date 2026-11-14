<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class PdfController extends Controller
{
    public function concatenate(Request $request)
    {
        // 1. Validate that 'files' is present and is an array
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
                if (!$file->isValid()) {
                    throw new \Exception("One of the uploaded files is invalid.");
                }
                
                // Ensure it's actually a PDF based on mime type
                if ($file->getMimeType() !== 'application/pdf') {
                    throw new \Exception("All uploaded files must be PDFs.");
                }

                $path = $file->store('pdfs'); 
                // Lumen's store() uses the local disk by default in simple setups
                // We get the absolute path to pass to the CLI
                $tempFiles[] = storage_path('app/' . $path);
            }

            // 3. Construct the pdfunite command
            // pdfunite file1.pdf file2.pdf output.pdf
            $inputFilesList = implode(' ', array_map('escapeshellarg', $tempFiles));
            $command = "pdfunite {$inputFilesList} " . escapeshellarg($outputFile);

            exec($command, $output, $returnVar);

            if ($returnVar !== 0) {
                throw new \Exception("pdfunite failed to concatenate files.");
            }

            // 4. Return the PDF file
            return new BinaryFileResponse($outputFile, 200, [
                'Content-Type' => 'application/pdf',
                'Content-Disposition' => 'attachment; filename="concatenated.pdf"',
            ]);

        } catch (\Exception $e) {
            return response()->json(['error' => 'An error occurred while processing the files: ' . $e->getMessage()], 500);
        } finally {
            // Cleanup temporary input files
            foreach ($tempFiles as $f) {
                if (file_exists($f)) {
                    @unlink($f);
                }
            }
            // Note: The output file is handled by BinaryFileResponse, 
            // but in a production environment, you'd use a cleanup callback or a cron.
        }
    }
}