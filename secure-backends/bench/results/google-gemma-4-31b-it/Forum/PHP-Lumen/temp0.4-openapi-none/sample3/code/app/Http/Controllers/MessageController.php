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

        // Generate simple HTML response as per OpenAPI spec (text/html)
        $html = "<html><head><title>MyForum</title></head><body>";
        $html .= "<h1>MyForum</h1>";
        $html .= "<form method='POST' action='/messages' style='margin-bottom: 20px;'>";
        $html .= "Username: <input type='text' name='username'><br>";
        $html .= "Message: <input type='text' name='content'><br>";
        $html .= "<button type='submit'>Post</button>";
        $html .= "</form>";
        $html .= "<hr><ul>";

        foreach ($messages as $msg) {
            $html .= "<li><strong>" . htmlspecialchars($msg->username) . "</strong>: " . htmlspecialchars($msg->content) . " <small>(" . $msg->created_at . ")</small></li>";
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

        $data = $request->only(['username', 'content']);
        Message::create($data);

        return response()->json(['status' => 'Successful operation'], 200);
    }
}