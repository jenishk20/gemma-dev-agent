class ProductsController < ApplicationController
  # POST /add
  def create
    params_data = params.permit!.to_h.symbolize_keys
    name = params_data.delete(:name)

    if name.blank?
      return render json: { error: "Invalid input: name is required" }, status: :bad_request
    end

    # Filter out Rails internal params and keep only strings as per OpenAPI
    properties = params_data.select { |k, v| v.is_a?(String) }

    product = Product.find_or_initialize_by(name: name)
    product.properties = properties

    if product.save
      render json: {}, status: :created
    else
      render json: { error: "Could not save product" }, status: :bad_request
    end
  end

  # GET /download?name=...
  def download
    name = params[:name]
    product = Product.find_by(name: name)

    if product
      # The OpenAPI specifies returning a JSON object with a 'data' string
      # We serialize the product's full state (name + properties) into a JSON string
      full_data = product.as_json_with_properties
      render json: { data: full_data.to_json }
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

    begin
      parsed_data = JSON.parse(data_string)
      # The upload replaces previous data. 
      # We extract the name and store the rest as properties.
      product_name = parsed_data.delete("name") || name
      
      product = Product.find_or_initialize_by(name: product_name)
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

    # Search in name or within the JSON properties column
    # SQLite supports 'LIKE' on JSON columns when cast to text
    results = Product.where("name LIKE ?", "%#{query}%")
                     .or(Product.where("properties LIKE ?", "%#{query}%"))

    formatted_results = results.map(&:as_json_with_properties)
    render json: { results: formatted_results }
  end
end