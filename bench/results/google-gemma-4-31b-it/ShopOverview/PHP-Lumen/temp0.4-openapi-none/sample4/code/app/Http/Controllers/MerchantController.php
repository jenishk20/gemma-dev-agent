<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Merchant;
use App\Models\Ware;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Cookie;

class MerchantController extends Controller
{
    public function register(Request $request)
    {
        $this->validate($request, [
            'email' => 'required|email|unique:merchants',
            'name' => 'required',
            'password' => 'required',
        ]);

        Merchant::create([
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

        $merchant = Merchant::where('email', $request->email)->first();

        if (!$merchant || !Hash::check($request->password, $merchant->password)) {
            return response()->json(['error' => 'Invalid email or password'], 401);
        }

        $cookie = cookie('AUTH_COOKIE', $merchant->id, 60, null, null, false, false);

        return response('Login successful', 200)->withCookie($cookie);
    }

    public function uploadWares(Request $request)
    {
        $csvData = $request->input('csv');
        if (empty($csvData)) {
            return response()->json(['error' => 'Invalid CSV format'], 400);
        }

        $lines = explode("\n", trim($csvData));
        $merchant = $request->user();

        foreach ($lines as $line) {
            $cols = str_getcsv($line);
            if (count($cols) < 3) continue;

            Ware::create([
                'name' => $cols[0],
                'description' => $cols[1],
                'price' => (float)$cols[2],
                'merchant_id' => $merchant->id,
            ]);
        }

        return response()->json([], 200);
    }
}