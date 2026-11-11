class ProductsController < ApplicationController
  # POST /add
  def add
    # Extract name and treat everything else as unstructured properties
    params_data = params.permit!.to_h
    name = params_data.delete("name")

    if name.blank?
      return render json: { error: "Name is required" }, status: :bad_request
    end

    product = Product.new(name: name, properties: params_data)
    if product.save
      render status: :created
    else
      render json: { error: product.errors.full_messages }, status: :bad_request
    end
  end

  # GET /download?name=...
  def download
    product = Product.find_by(name: params[:name])
    if product
      # The schema asks for the "data" of the product. 
      # We return the JSON string of its properties.
      render json: { data: product.properties.to_json }
    else
      render json: { error: "Product not found" }, status: :not_found
    end
  end

  # POST /upload
  def upload
    name = params[:name]
    data_string = params[:data]

    if name.blank? || data_string.blank?
      return render json: { error: "Invalid upload query" }, status: :bad_request
    end

    product = Product.find_or_initialize_by(name: name)
    begin
      # Parse the data string back into a hash
      parsed_properties = JSON.parse(data_string)
      product.properties = parsed_properties
      
      if product.save
        render json: { message: "The product with the given name was updated." }, status: :ok
      else
        render json: { error: product.errors.full_messages }, status: :bad_request
      end
    rescue JSON::ParserError
      render json: { error: "Invalid JSON data" }, status: :bad_request
    end
  end

  # GET /search?query=...
  def search
    query = params[:query]
    if query.blank?
      return render json: { error: "Invalid search query" }, status: :bad_request
    end

    # Search in name OR in the properties JSON column
    # SQLite's LIKE operator works on the JSON text
    products = Product.where("name LIKE ? OR properties LIKE ?", "%#{query}%", "%#{query}%")
    
    results = products.map do |p|
      p.full_attributes
    end

    render json: { results: results }
  end
end