<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Ware;

class WareController extends Controller
{
    public function index(Request $request)
    {
        $query = Ware::with('merchant');

        if ($request->has('minPrice')) {
            $query->where('price', '>=', $request->minPrice);
        }

        if ($request->has('maxPrice')) {
            $query->where('price', '<=', $request->maxPrice);
        }

        $wares = $query->get();

        $html = '<table border="1"><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant Email</th></tr></thead><tbody>';
        foreach ($wares as $ware) {
            $html .= "<tr><td>{$ware->name}</td><td>{$ware->price}</td><td>{$ware->description}</td><td>{$ware->merchant->email}</td></tr>";
        }
        $html .= '</tbody></table>';

        return response($html, 200)->header('Content-Type', 'text/html');
    }
}