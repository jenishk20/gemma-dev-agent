<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\User;
use App\Models\Ware;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Cookie;

class WarehouseController extends Controller
{
    public function register(Request $request)
    {
        $this->validate($request, [
            'email' => 'required|email|unique:users',
            'name' => 'required|string',
            'password' => 'required|string',
        ]);

        User::create([
            'email' => $request->email,
            'name' => $request->name,
            'password' => Hash::make($request->password),
        ]);

        return response()->json([], 201);
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

        // Set a cookie with the user ID as a simple auth token
        return response('Login successful', 200)
            ->cookie('AUTH_COOKIE', $user->id, 60*24*7);
    }

    public function uploadWares(Request $request)
    {
        if (!$request->user()) {
            return response()->json(['error' => 'Unauthorized'], 401);
        }

        $this->validate($request, ['csv' => 'required|string']);
        $csvData = $request->input('csv');
        $lines = explode("\n", trim($csvData));
        
        foreach ($lines as $line) {
            $cols = str_getcsv($line);
            if (count($cols) < 3) continue;
            
            Ware::create([
                'name' => $cols[0],
                'description' => $cols[1],
                'price' => (float)$cols[2],
                'user_id' => $request->user()->id
            ]);
        }

        return response()->json([], 200);
    }

    public function listWares(Request $request)
    {
        if (!$request->user()) {
            return response()->json(['error' => 'Unauthorized'], 401);
        }

        $query = Ware::with('merchant');

        if ($request->has('minPrice')) {
            $query->where('price', '>=', $request->minPrice);
        }
        if ($request->has('maxPrice')) {
            $query->where('price', '<=', $request->maxPrice);
        }

        $wares = $query->get();

        $html = '<table border="1"><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr></thead><tbody>';
        foreach ($wares as $ware) {
            $html .= sprintf(
                '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>',
                htmlspecialchars($ware->name),
                htmlspecialchars($ware->price),
                htmlspecialchars($ware->description),
                htmlspecialchars($ware->merchant->email)
            );
        }
        $html .= '</tbody></table>';

        return response($html, 200)->header('Content-Type', 'text/html');
    }
}