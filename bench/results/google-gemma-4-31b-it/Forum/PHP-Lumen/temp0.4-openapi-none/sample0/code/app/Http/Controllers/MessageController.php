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

        $messages = Message::orderBy('created_at', $sort)
            ->offset($offset)
            ->limit($limit)
            ->get();

        $html = "<html><head><title>MyForum</title></head><body>";
        $html .= "<h1>Forum Messages</h1>";
        $html .= "<form method='POST' action='/messages' style='margin-bottom: 20px;'>";
        $html .= "Username: <input type='text' name='username'><br>";
        $html .= "Message: <input type='text' name='content'><br>";
        $html .= "<input type='submit' value='Post'>";
        $html .= "</form><hr>";

        foreach ($messages as $msg) {
            $html .= "<div><strong>" . htmlspecialchars($msg->username) . "</strong>: " . htmlspecialchars($msg->content) . " <small>(" . $msg->created_at . ")</small></div><br>";
        }

        $html .= "</body></html>";

        return response($html)->header('Content-Type', 'text/html');
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

        return response()->json([], 200);
    }
}