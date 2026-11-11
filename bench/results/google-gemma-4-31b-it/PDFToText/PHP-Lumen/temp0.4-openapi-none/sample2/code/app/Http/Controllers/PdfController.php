<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\ResponseHeaderBag;

class PdfController extends Controller
{
    public function convert(Request $request)
    {
        // 1. Validate that the file exists in the request
        if (!$request->hasFile('file')) {
            return response()->json(['error' => 'No file uploaded'], 400);
        }

        $file = $request->file('file');

        // 2. Validate that the file is actually a PDF
        $mimeType = $file->getMimeType();
        if ($mimeType !== 'application/pdf') {
            return response()->json(['error' => 'Invalid file type. Please upload a PDF.'], 400);
        }

        // 3. Store the file temporarily
        $tempPath = tempnam(sys_get_temp_dir(), 'pdf_conv_');
        $file->move(dirname($tempPath), basename($tempPath));

        try {
            // 4. Use pdftotext utility
            // - says: output to stdout (-)
            $command = sprintf('pdftotext %s -', escapeshellarg($tempPath));
            $output = shell_exec($command);

            if ($output === null) {
                throw new \Exception('Failed to extract text from PDF');
            }

            // 5. Return as plain text
            return response($output, 200)
                ->header('Content-Type', 'text/plain');

        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal Server Error - Conversion failed'], 500);
        } finally {
            // Clean up temporary file
            if (file_exists($tempPath)) {
                unlink($tempPath);
            }
        }
    }
}