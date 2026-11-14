<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Message;

class MessageController extends Controller
{
    public function index(Request $request)
    {
        $limit = $request->query('limit', 10);
        $offset = $request->query('offset', 0);
        $sort = strtoupper($request->query('sort', 'DESC'));

        $query = Message::query();

        if ($sort === 'ASC') {
            $query->orderBy('created_at', 'asc');
        } else {
            $query->orderBy('created_at', 'desc');
        }

        $messages = $query->offset($offset)->limit($limit)->get();

        // Generating simple HTML response as per OpenAPI spec (text/html)
        $html = "<html><body><h1>Forum Messages</h1><ul>";
        foreach ($messages as $msg) {
            $html .= "<li><strong>{$msg->username}</strong>: {$msg->content} <small>({$msg->created_at})</small></li>";
        }
        $html .= "</ul></body></html>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function store(Request $request)
    {
        $this->validate($request, [
            'username' => 'required|string',
            'content' => 'required|string',
        ]);

        Message::create([
            'username' => $request->input('username'),
            'content' => $request->input('content'),
        ]);

        return response()->json(['status' => 'Successful operation'], 200);
    }
}