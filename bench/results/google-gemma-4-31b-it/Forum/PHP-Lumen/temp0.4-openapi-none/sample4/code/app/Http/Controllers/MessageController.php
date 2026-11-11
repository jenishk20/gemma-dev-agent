<?php

namespace App\Http\Controllers;

use App\Models\Message;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

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

        // The OpenAPI spec requires text/html response for GET /messages
        $html = "<html><head><title>MyForum</title></head><body>";
        $html .= "<h1>Forum Messages</h1>";
        $html .= "<ul>";
        foreach ($messages as $msg) {
            $html .= "<li><strong>" . htmlspecialchars($msg->username) . "</strong>: " . htmlspecialchars($msg->content) . " <small>(" . $msg->created_at . ")</small></li>";
        }
        $html .= "</ul>";
        $html .= "</body></html>";

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

        return response('', 200);
    }
}