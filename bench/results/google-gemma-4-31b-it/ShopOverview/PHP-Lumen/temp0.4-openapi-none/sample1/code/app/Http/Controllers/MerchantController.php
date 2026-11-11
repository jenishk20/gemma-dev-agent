<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\User;
use App\Models\Ware;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Cookie;

class MerchantController extends Controller
{
    public function register(Request $request)
    {
        $this->validate($request, [
            'email' => 'required|email|unique:users',
            'name' => 'required|string',
            'password' => 'required|string',
        ]);

        User::create([
            'name' => $request->name,
            'email' => $request->email,
            'password' => Hash::make($request->password),
        ]);

        return response()->json(['message' => 'Merchant registered successfully'], 201);
    }

    public function login(Request $request)
    {
        $this->validate($request, [
            'email' => 'required|email',
            'password' => 'required',
        ]);

        $user = User::where('email', $request->email)->first();

        if (!$user || !Hash::check($request->password, $user->password)) {
            return response()->json(['error' => 'Invalid email or password'], 401);
        }

        $cookie = cookie('AUTH_COOKIE', $user->id, 60 * 24); // 24 hours
        return response('Login successful', 200)->withCookie($cookie);
    }

    public function uploadWares(Request $request)
    {
        if (!Auth::user()) {
            return response()->json(['error' => 'Unauthorized'], 401);
        }

        $csvData = $request->input('csv');
        if (empty($csvData)) {
            return response()->json(['error' => 'Invalid CSV format'], 400);
        }

        $lines = explode("\n", str_replace("\r", "", trim($csvData)));
        $userId = Auth::id();

        foreach ($lines as $line) {
            $data = str_getcsv($line);
            if (count($data) < 3) continue;

            Ware::create([
                'name' => $data[0],
                'description' => $data[1],
                'price' => (float)$data[2],
                'user_id' => $userId,
            ]);
        }

        return response()->json(['message' => 'Wares uploaded successfully'], 200);
    }

    public function listWares(Request $request)
    {
        if (!Auth::user()) {
            return response()->json(['error' => 'Unauthorized'], 401);
        }

        $query = Ware::with('user');

        if ($request->has('minPrice')) {
            $query->where('price', '>=', $request->minPrice);
        }
        if ($request->has('maxPrice')) {
            $query->where('price', '<=', $request->maxPrice);
        }

        $wares = $query->get();

        $html = '<table border="1"><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant Email</th></tr></thead><tbody>';
        foreach ($wares as $ware) {
            $html .= "<tr><td>{$ware->name}</td><td>{$ware->price}</td><td>{$ware->description}</td><td>{$ware->user->email}</td></tr>";
        }
        $html .= '</tbody></table>';

        return response($html, 200)->header('Content-Type', 'text/html');
    }
}