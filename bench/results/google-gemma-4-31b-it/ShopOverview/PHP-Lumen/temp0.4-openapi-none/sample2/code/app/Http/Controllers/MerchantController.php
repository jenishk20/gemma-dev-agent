<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Merchant;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Cookie;

class MerchantController extends Controller
{
    public function register(Request $request)
    {
        $this->validate($request, [
            'email' => 'required|email|unique:merchants',
            'name' => 'required|string',
            'password' => 'required|string',
        ]);

        Merchant::create([
            'email' => $request->email,
            'name' => $request->name,
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

        $merchant = Merchant::where('email', $request->email)->first();

        if (!$merchant || !Hash::check($request->password, $merchant->password)) {
            return response()->json(['error' => 'Invalid email or password'], 401);
        }

        // Simple session cookie using the merchant ID encrypted
        $cookieValue = encrypt($merchant->id);
        return response('Login successful', 200)
            ->cookie('AUTH_COOKIE', $cookieValue, 60, null, null, false, true);
    }

    public function uploadWares(Request $request)
    {
        $this->validate($request, ['csv' => 'required|string']);
        
        $csvData = $request->input('csv');
        $lines = explode("\n", trim($csvData));
        $merchantId = decrypt(Cookie::get('AUTH_COOKIE'));

        foreach ($lines as $line) {
            $data = str_getcsv($line);
            if (count($data) < 3) continue;

            \App\Models\Ware::create([
                'merchant_id' => $merchantId,
                'name' => $data[0],
                'description' => $data[1],
                'price' => (float)$data[2],
            ]);
        }

        return response()->json(['message' => 'Wares uploaded successfully'], 200);
    }
}