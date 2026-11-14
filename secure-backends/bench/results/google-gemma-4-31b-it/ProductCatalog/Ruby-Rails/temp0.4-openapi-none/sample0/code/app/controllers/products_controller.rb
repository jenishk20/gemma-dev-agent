class ProductsController < ApplicationController
  # POST /add
  def add
    # Extract name and separate it from additional properties
    params_data = params.permit!.to_h
    name = params_data.delete("name")

    if name.blank?
      return render json: { error: "Invalid input: name is required" }, status: :bad_request
    end

    # The remaining params_data are the unstructured properties
    product = Product.create(name: name, properties: params_data)

    if product.persisted?
      render json: {}, status: :created
    else
      render json: { error: "Could not create product" }, status: :bad_request
    end
  end

  # GET /download?name=...
  def download
    product = Product.find_by(name: params[:name])
    if product
      # The OpenAPI specifies returning the data as a string. 
      # We store the properties as a JSON string.
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
    
    # Parse the data string to ensure it's valid JSON before saving
    begin
      parsed_data = JSON.parse(data_string)
      product.properties = parsed_data
      if product.save
        render json: { message: "The product with the given name was updated." }, status: :ok
      else
        render json: { error: "Save failed" }, status: :bad_request
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

    products = Product.search(query)
    results = products.map(&:as_json_with_properties)
    
    render json: { results: results }
  end
end