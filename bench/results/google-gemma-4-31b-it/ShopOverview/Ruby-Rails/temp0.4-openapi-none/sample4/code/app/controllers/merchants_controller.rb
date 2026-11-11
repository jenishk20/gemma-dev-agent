require 'csv'

class MerchantsController < ApplicationController
  def register
    merchant = Merchant.new(merchant_params)
    if merchant.save
      render json: { message: 'Merchant registered successfully' }, status: :created
    else
      render json: { error: 'Invalid input' }, status: :bad_request
    end
  end

  def login
    merchant = Merchant.find_by(email: params[:email])
    if merchant&.authenticate(params[:password])
      cookies.signed[:merchant_id] = { value: merchant.id, httponly: true }
      render json: 'Login successful', status: :ok
    else
      render json: { error: 'Invalid email or password' }, status: :unauthorized
    end
  end

  def upload_wares
    authenticate_merchant!
    
    csv_data = params[:csv]
    if csv_data.blank?
      return render json: { error: 'Invalid CSV format' }, status: :bad_request
    end

    begin
      CSV.parse(csv_data, headers: true) do |row|
        # Expected columns: name, description, price
        Ware.create!(
          name: row['name'],
          description: row['description'],
          price: row['price'].to_f,
          merchant: current_merchant
        )
      end
      render json: { message: 'Wares uploaded successfully' }, status: :ok
    rescue CSV::MalformedCSVError, ActiveRecord::RecordInvalid
      render json: { error: 'Invalid CSV format' }, status: :bad_request
    end
  end

  private

  def merchant_params
    params.permit(:email, :name, :password)
  end
end