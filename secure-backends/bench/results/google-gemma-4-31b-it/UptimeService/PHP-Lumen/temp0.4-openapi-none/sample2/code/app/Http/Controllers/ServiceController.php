<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Service;
use Illuminate\Support\Carbon;

class ServiceController extends Controller
{
    public function heartbeat(Request $request)
    {
        $this->validate($request, [
            'serviceId' => 'required|string',
            'token' => 'required|string',
        ]);

        $serviceId = $request->input('serviceId');
        $token = $request->input('token');

        try {
            Service::updateOrCreate(
                ['serviceId' => $serviceId],
                [
                    'token' => $token,
                    'lastNotification' => Carbon::now()
                ]
            );

            return response()->json([], 200);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal server error'], 500);
        }
    }

    public function overview(Request $request)
    {
        $this->validate($request, [
            'token' => 'required|string',
        ]);

        $token = $request->input('token');

        try {
            $services = Service::where('token', $token)
                ->get(['serviceId', 'lastNotification']);

            $result = $services->map(function ($service) {
                return [
                    'serviceId' => $service->serviceId,
                    'lastNotification' => $service->lastNotification->toIso8601String(),
                ];
            });

            return response()->json($result, 200);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal server error'], 500);
        }
    }
}