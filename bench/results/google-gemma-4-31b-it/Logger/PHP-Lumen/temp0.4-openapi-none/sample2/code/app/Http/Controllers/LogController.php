<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;

class LogController extends Controller
{
    private $filePath = 'logs.txt';

    public function store(Request $request)
    {
        $this->validate($request, [
            'message' => 'required|string',
        ]);

        $message = $request->input('message');
        
        // Append the message and a newline to the file
        // FILE_APPEND ensures we don't overwrite existing logs
        file_put_contents(storage_path($this->filePath), $message . PHP_EOL, FILE_APPEND);

        return response()->json(['status' => 'Log message successful'], 200);
    }

    public function index()
    {
        $path = storage_path($this->filePath);

        if (!File::exists($path)) {
            return response('', 200)->header('Content-Type', 'text/plain');
        }

        $content = File::get($path);
        
        return response($content, 200)->header('Content-Type', 'text/plain');
    }
}