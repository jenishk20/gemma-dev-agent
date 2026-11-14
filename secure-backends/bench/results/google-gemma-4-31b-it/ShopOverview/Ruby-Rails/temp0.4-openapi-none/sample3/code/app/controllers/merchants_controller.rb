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
      cookies.signed[:AUTH_COOKIE] = { value: merchant.id, httponly: true }
      render json: 'Login successful', status: :ok
    else
      render json: { error: 'Invalid email or password' }, status: :unauthorized
    end
  end

  def upload_wares
    authenticate_merchant!
    return unless @current_merchant

    begin
      csv_data = params[:csv]
      return render json: { error: 'No CSV provided' }, status: :bad_request if csv_data.blank?

      CSV.parse(csv_data, headers: true) do |row|
        @current_merchant.wares.create!(
          name: row['name'],
          description: row['description'],
          price: row['price'].to_f
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