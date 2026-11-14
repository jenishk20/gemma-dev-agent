<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Cart;
use App\Models\CartItem;
use Illuminate\Support\Str;

class CartController extends Controller
{
    public function create(Request $request)
    {
        $cart = Cart::create([
            'cart_id' => Str::uuid()->toString()
        ]);

        return response()->json(['cart_id' => $cart->cart_id], 201);
    }

    public function add(Request $request)
    {
        $this->validate($request, [
            'cart_id' => 'required|string',
            'item_id' => 'required|integer',
            'count' => 'required|integer',
        ]);

        $cart = Cart::where('cart_id', $request->input('cart_id'))->first();

        if (!$cart) {
            return response()->json(['error' => 'Cart not found'], 404);
        }

        $item = CartItem::where('cart_id', $cart->cart_id)
                        ->where('item_id', $request->input('item_id'))
                        ->first();

        if ($item) {
            $item->count += $request->input('count');
            if ($item->count <= 0) {
                $item->delete();
            } else {
                $item->save();
            }
        } else {
            $count = $request->input('count');
            if ($count > 0) {
                CartItem::create([
                    'cart_id' => $cart->cart_id,
                    'item_id' => $request->input('item_id'),
                    'count' => $count
                ]);
            }
        }

        return response()->json(null, 200);
    }

    public function retrieve(Request $request)
    {
        $this->validate($request, [
            'cart_id' => 'required|string',
        ]);

        $cart = Cart::where('cart_id', $request->input('cart_id'))->first();

        if (!$cart) {
            return response()->json(['error' => 'Cart not found'], 404);
        }

        $items = CartItem::where('cart_id', $cart->cart_id)
                         ->get(['item_id', 'count']);

        return response()->json(['items' => $items], 200);
    }
}