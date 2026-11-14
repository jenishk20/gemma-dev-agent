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

        $html = '<table>';
        $html .= '<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>';
        
        foreach ($wares as $ware) {
            $html .= sprintf(
                '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>',
                htmlspecialchars($ware->name),
                htmlspecialchars($ware->price),
                htmlspecialchars($ware->description),
                htmlspecialchars($ware->merchant->email)
            );
        }
        $html .= '</table>';

        return response($html, 200)->header('Content-Type', 'text/html');
    }
}