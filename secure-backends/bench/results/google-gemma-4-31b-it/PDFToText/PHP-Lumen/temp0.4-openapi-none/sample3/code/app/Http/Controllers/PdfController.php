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

        // 2. Validate that the file is a PDF
        // We check the extension and the mime type
        $extension = $file->getClientOriginalExtension();
        $mimeType = $file->getMimeType();

        if ($extension !== 'pdf' && $mimeType !== 'application/pdf') {
            return response()->json(['error' => 'Invalid file type. Please upload a PDF.'], 400);
        }

        try {
            // 3. Store file temporarily to process it
            $tempPath = tempnam(sys_get_temp_dir(), 'pdf_');
            $file->move(dirname($tempPath), basename($tempPath));

            // 4. Use pdftotext to extract text
            // '-' tells pdftotext to output to stdout
            $command = sprintf('pdftotext %s -', escapeshellarg($tempPath));
            $text = shell_exec($command);

            // Clean up temporary file
            if (file_exists($tempPath)) {
                unlink($tempPath);
            }

            if ($text === null) {
                throw new \Exception("Conversion failed to produce output.");
            }

            // 5. Return as plain text as per OpenAPI spec
            return response($text, 200)
                ->header('Content-Type', 'text/plain');

        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal Server Error - Conversion failed: ' . $e->getMessage()], 500);
        }
    }
}